from attrs import define, field, validators
from pathlib import Path
from typing import Any
import yaml


DEFAULT_CONFIG = Path(__file__).parent.parent / "config.yaml"


@define
class VoskModel:
    model: str


VALID_WHISPER_MODELS = {
    "base", "large", "large-v1", "large-v2",
    "tiny", "small", "medium",
    "tiny.en", "small.en", "medium.en"
}

VALID_WHISPER_LIBRARIES = {
    "openai-whisper", "whisper-timestamped", "stable-whisper"
}


@define
class WhisperModel:
    name: str = field(validator=validators.in_(VALID_WHISPER_MODELS))
    device: str | None = None
    library: str = field(default="openai-whisper", validator=validators.in_(VALID_WHISPER_LIBRARIES))


VALID_ÉTOILE_EXPORT_FORMATS = {
    "json", "audacity", "audition"
}


@define
class ÉtoileSettings:
    export_format: str = field(default="json", validator=validators.in_(VALID_ÉTOILE_EXPORT_FORMATS))


VALID_HOSHI_RECONCILIATION_MODELS = {
    "simple", "assisted", "always-assisted"
}


@define
class HoshiSettings:
    reconciliation: str = field(default="assisted", validator=validators.in_(VALID_HOSHI_RECONCILIATION_MODELS))


VALID_ASTRAL_ALIGNMENT_MODES = {
    "fixed", "word"
}


@define
class AstralSettings:
    initial_indent: int = field(default=4, validator=[validators.instance_of(int), validators.ge(0)])
    additional_indent: int = field(default=4, validator=[validators.instance_of(int), validators.ge(0)])
    alignment: str = field(default="fixed", validator=validators.in_(VALID_ASTRAL_ALIGNMENT_MODES))
    frame_length: float = field(default=0.2, validator=[validators.instance_of(float), validators.gt(0)])


VALID_UI_THEMES = {
    # light themes
    "cosmo", "flatly", "journal", "litera", "lumen", "minty",
    "pulse", "sandstone", "united", "yeti", "morph", "simplex", "cerculean",

    # dark themes
    "solar", "superhero", "darkly", "cyborg", "vapor"
}


@define
class UIThemes:
    stlr: str = field(validator=validators.in_(VALID_UI_THEMES))
    astral: str = field(validator=validators.in_(VALID_UI_THEMES))
    hoshi: str = field(validator=validators.in_(VALID_UI_THEMES))


@define
class Config:
    model: WhisperModel
    whisper: dict[str, Any]
    vosk: VoskModel
    astral: AstralSettings
    hoshi: HoshiSettings
    étoile: ÉtoileSettings
    ui_themes: UIThemes

    @classmethod
    def load(cls, path: Path = DEFAULT_CONFIG):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        ws: dict[str, Any] = data["whisper_settings"]
        model_config = WhisperModel(name=ws.pop("model"), device=ws.pop("device"), library=ws.pop("library"))
        return cls(
            model_config,
            ws,
            VoskModel(**data["vosk_settings"]),
            AstralSettings(**data["astral_settings"]),
            HoshiSettings(**data["hoshi_settings"]),
            ÉtoileSettings(**data["étoile_settings"]),
            UIThemes(**data["ui_themes"])
        )


CONFIG = Config.load()
