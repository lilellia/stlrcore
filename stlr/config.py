from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
import yaml


DEFAULT_CONFIG = Path(__file__).parent.parent / "config.yaml"


@dataclass
class WhisperModel:
    name: str
    device: str | None


@dataclass
class UIThemes:
    stlr: str
    astral: str


@dataclass
class Config:
    model: WhisperModel
    whisper: dict[str, Any]
    ui_themes: UIThemes

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG):
        with open(path) as f:
            data = yaml.safe_load(f)

        ws: dict[str, Any] = data["whisper_settings"]
        model_config = WhisperModel(name=ws.pop("model"), device=ws.pop("device"))
        return cls(model_config, ws, UIThemes(**data["ui_themes"]))


CONFIG = Config.load()
