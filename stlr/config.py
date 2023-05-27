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
class ÉtoileSettings:
    export_format: str = "json"


@dataclass
class UIThemes:
    stlr: str
    astral: str


@dataclass
class Config:
    transcription_models: TranscriptionModels
    whisper_settings: dict[str, Any]
    étoile_settings: ÉtoileSettings
    ui_themes: UIThemes

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG):
        with open(path) as f:
            data = yaml.safe_load(f)

        return cls(
            TranscriptionModels(**data["transcription_models"]),
            data["whisper_settings"],
            ÉtoileSettings(**data["étoile_settings"]),
            UIThemes(**data["ui_themes"])
        )


CONFIG = Config.load()
