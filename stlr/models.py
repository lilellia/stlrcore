from difflib import SequenceMatcher
import json
from loguru import logger
from pathlib import Path
from pprint import pprint
import re
import stable_whisper
from stable_whisper.result import WordTiming
from termcolor import colored
from typing import Any, Protocol
import vosk
import wave
import whisper
import whisper_timestamped

import stlr

# disable vosk's logging
vosk.SetLogLevel(-1)


class Model(Protocol):
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        ...

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> stable_whisper.WhisperResult:
        ...


class OpenAIWhisper:
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        self.whisper_model = whisper.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> stable_whisper.WhisperResult:
        vosk_model = kwargs.pop("vosk_model", "vosk-model-small-en-us-0.15")
        vosk_result = self._vosk_transcribe(audio_file, model_name=vosk_model)
        whisper_result: dict[str, Any] = self.whisper_model.transcribe(str(audio_file), **kwargs)  # type: ignore

        return self.reconcile(whisper_result, vosk_result)

    def _get_vosk_recognizer(self, audio: wave.Wave_read, model_name: str = stlr.config.CONFIG.vosk.model) -> vosk.KaldiRecognizer:
        model = vosk.Model(model_name=model_name)

        r = vosk.KaldiRecognizer(model, audio.getframerate())
        r.SetMaxAlternatives(10)
        r.SetWords(True)

        return r

    def _vosk_transcribe(self, audio_file: str | Path, model_name: str = stlr.config.CONFIG.vosk.model) -> list[WordTiming]:
        audio = stlr.audio_utils.load_audio(audio_file)
        r = self._get_vosk_recognizer(audio, model_name)

        def _partial(result: Any) -> list[WordTiming]:
            """Transcribe a section of audio, defined by the result str"""
            data = json.loads(result)
            words = data["alternatives"][0]["result"]
            return [WordTiming(word=word["word"], start=word["start"], end=word["end"]) for word in words]

        result: list[WordTiming] = []
        while data := audio.readframes(4096):
            if not r.AcceptWaveform(data):
                continue

            result.extend(_partial(r.Result()))

        result.extend(_partial(r.FinalResult()))
        return result

    def reconcile(self, whisper_result: dict[str, Any], vosk_result: list[WordTiming]) -> stable_whisper.WhisperResult:
        whisper_words = len(whisper_result["text"].split())
        vosk_words = len(vosk_result)

        if whisper_words == vosk_words:
            logger.info(f"# of words match between whisper & vosk transcriptions ({whisper_words})")
            logger.info(f"assigning vosk timings onto whisper transcription")

            return self._reconcile_matching(whisper_result, vosk_result)

        logger.warning(f"# of words differ between transcriptions: whisper ({whisper_words}) / vosk ({vosk_words})")
        logger.warning(f"whisper: {whisper_result['text']}")
        logger.warning(f"   vosk: {' '.join(w.word for w in vosk_result)}")
        return self._reconcile_unmatching(whisper_result, vosk_result)

    @staticmethod
    def _reconcile_matching(whisper_result: dict[str, Any], vosk_result: list[WordTiming]) -> stable_whisper.WhisperResult:
        """Construct a WhisperResult by combining the timing results from vosk with the untimed transcription from whisper."""
        resolved: dict[str, Any] = whisper_result
        viter = iter(vosk_result)

        segment: dict[str, Any]
        for segment in resolved["segments"]:
            segment["words"] = [v for v, _ in zip(viter, segment["text"].split())]

        assert next(viter, None) is None

        return stable_whisper.WhisperResult(resolved)

    @staticmethod
    def _reconcile_unmatching(whisper_result: dict[str, Any], vosk_result: list[WordTiming]) -> stable_whisper.WhisperResult:
        """Resolve an unmatching pair of results by allowing hoshi to intercede."""

        if stlr.config.CONFIG.hoshi.reconciliation in {"naive", "naïve"}:
            resolved: dict[str, Any] = {
                "language": whisper_result.get("language", "en"),
                "segments": [
                    {
                        "start": min(w.start for w in vosk_result),
                        "end": max(w.end for w in vosk_result),
                        "words": vosk_result,
                        "text": " ".join(w.word for w in vosk_result)
                    }
                ]
            }
            
            return stable_whisper.WhisperResult(resolved)
        
        # otherwise, perform assisted reconciliation
        hoshi = stlr.ui.HoshiApp("星 hoshi", themename="darkly", whisper_result=whisper_result, vosk_result=vosk_result)
        hoshi.mainloop()  # modifies whisper_result in place

        return stable_whisper.WhisperResult(whisper_result)


class StableWhisper:
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        self.model = stable_whisper.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> stable_whisper.WhisperResult:
        return self.model.transcribe(str(audio_file), **kwargs)  # type: ignore


class WhisperTimestamped:
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        self.model = whisper_timestamped.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> stable_whisper.WhisperResult:
        result = whisper_timestamped.transcribe(self.model, str(audio_file), **kwargs)
        return stable_whisper.WhisperResult(result)


class ModelManager:
    def __init__(self):
        self.models: dict[tuple[str, str], Model] = dict()

    def get(self, library: str, model_name: str, device: str | None) -> Model:
        LOAD_LOOKUP = {
            "openai-whisper": OpenAIWhisper,
            "whisper-timestamped": WhisperTimestamped,
            "stable-whisper": StableWhisper
        }

        if library not in LOAD_LOOKUP:
            raise ValueError(f"invalid library: {library!r}")

        key = (library, model_name)

        if key not in self.models:
            self.models[key] = LOAD_LOOKUP[library](model_name, device)

        return self.models[key]
