import json
from pathlib import Path
import stable_whisper
from stable_whisper.result import WordTiming
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

        return stlr.hoshi.reconcile(whisper_result, vosk_result, mode=stlr.config.CONFIG.hoshi.reconciliation)

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
