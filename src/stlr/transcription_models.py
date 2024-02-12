from __future__ import annotations

from pathlib import Path
from typing import Protocol, Any

import stable_whisper
import whisper_timestamped

from src.stlr.transcribe import Transcription, WordTiming


class TranscriptionModel(Protocol):
    def __init__(
        self,
        name: str,
        device: str | None = None,
        download_root: str | None = None,
        in_memory: bool = False,
    ): ...

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> Transcription: ...


class StableWhisper:
    def __init__(
        self,
        name: str,
        device: str | None = None,
        download_root: str | None = None,
        in_memory: bool = False,
    ):
        self.model = stable_whisper.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> Transcription:
        result = self.model.transcribe(str(audio_file), **kwargs)  # type: ignore

        original_word_timings = [
            w
            for segment in result.segments
            for w in (
                segment.words or []
            )  # use "or []" since segment.words might be None instead
        ]

        # convert to our own WordTiming format
        word_timings = [
            WordTiming(word=x.word, start=x.start, end=x.end)
            for x in original_word_timings
        ]
        return Transcription(word_timings)


class WhisperTimestamped:
    def __init__(
        self,
        name: str,
        device: str | None = None,
        download_root: str | None = None,
        in_memory: bool = False,
    ):
        self.model = whisper_timestamped.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> Transcription:
        result = whisper_timestamped.transcribe(self.model, str(audio_file), **kwargs)  # type: ignore

        word_timings: list[WordTiming] = []
        for segment in result["segments"]:
            for word in segment["words"]:
                # convert this dictionary to a WordTiming and append
                timing = WordTiming(
                    word=word["text"],
                    start=word["start"],
                    end=word["end"],
                    confidence=word["confidence"],
                )
                word_timings.append(timing)

        return Transcription(word_timings)


class ModelCache:
    def __init__(self):
        self.models: dict[tuple[str, str], TranscriptionModel] = dict()

    def get(self, library: str, model_name: str, device: str | None) -> TranscriptionModel:
        lookup = {
            "whisper-timestamped": WhisperTimestamped,
            "stable-whisper": StableWhisper,
        }

        if library not in lookup:
            raise ValueError(f"invalid library: {library!r}")

        key = (library, model_name)

        if key not in self.models:
            self.models[key] = lookup[library](model_name, device)

        return self.models[key]


MODEL_CACHE = ModelCache()
