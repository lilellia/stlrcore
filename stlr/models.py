from pathlib import Path
from typing import Any, Protocol

import stable_whisper
import whisper
import whisper_timestamped


class Model(Protocol):
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        ...

    def transcribe(self, audio: str | Path, **kwargs: Any) -> stable_whisper.WhisperResult:
        ...


class OpenAIWhisper:
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        self.model = whisper.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio: str | Path, **kwargs: Any) -> stable_whisper.WhisperResult:
        result = self.model.transcribe(str(audio), **kwargs)  # type: ignore
        return stable_whisper.WhisperResult(result)


class StableWhisper:
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        self.model = stable_whisper.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio: str | Path, **kwargs: Any) -> stable_whisper.WhisperResult:
        return self.model.transcribe(str(audio), **kwargs)  # type: ignore


class WhisperTimestamped:
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        self.model = whisper_timestamped.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio: str | Path, **kwargs: Any) -> stable_whisper.WhisperResult:
        result = whisper_timestamped.transcribe(self.model, str(audio), **kwargs)
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
