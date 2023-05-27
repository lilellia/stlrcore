from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import yaml


DEFAULT_CONFIG = Path(__file__).parent.parent / "config.yaml"


@dataclass
class TranscriptionModels:
    whisper: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class WhisperSettings:
    language: str = "en"

    no_speech_threshold: float = 0.6
    logprob_threshold: float | None = -1.0

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UIThemes:
    stlr: str
    astral: str


@dataclass
class Config:
    transcription_models: TranscriptionModels
    whisper_settings: WhisperSettings
    ui_themes: UIThemes

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG):
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(
            TranscriptionModels(**data["transcription_models"]),
            WhisperSettings(**data["whisper_settings"]),
            UIThemes(**data["ui_themes"])
        )


CONFIG = Config.load()
