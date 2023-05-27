from dataclasses import dataclass
from pathlib import Path
from typing import Any
import yaml


DEFAULT_CONFIG = Path(__file__).parent.parent / "config.yaml"


@dataclass
class WhisperModel:
    name: str
    device: str | None


@dataclass
class ÉtoileSettings:
    export_format: str = "json"


@dataclass
class UIThemes:
    stlr: str
    astral: str


@dataclass
class Config:
    model: WhisperModel
    whisper: dict[str, Any]
    étoile: ÉtoileSettings
    ui_themes: UIThemes

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        ws: dict[str, Any] = data["whisper_settings"]
        model_config = WhisperModel(name=ws.pop("model"), device=ws.pop("device"))

        return cls(
            model_config,
            ws,
            ÉtoileSettings(**data["étoile_settings"]),
            UIThemes(**data["ui_themes"])
        )


CONFIG = Config.load()
