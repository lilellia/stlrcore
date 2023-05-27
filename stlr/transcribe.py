import csv
from dataclasses import asdict, dataclass
from more_itertools import windowed
import json
from pathlib import Path
from tabulate import tabulate
from typing import Any, Iterable, Iterator, Literal

from stlr.config import CONFIG
from stlr.models import ModelManager
from stlr.utils import seconds_to_hms

WHISPER_MODEL = CONFIG.model.name
WHISPER_DEVICE = CONFIG.model.device
WHISPER_SETTINGS = CONFIG.whisper


models = ModelManager()


@dataclass
class TranscribedWord:
    text: str
    start: float
    end: float
    confidence: float

    @property
    def duration(self) -> float:
        """Return the length of time the word is spoken."""
        return self.end - self.start

    def __str__(self) -> str:
        return f"{self.text}({self.start}-{self.end}/{self.duration:.3f})"


class Transcription:
    def __init__(self, words: Iterable[TranscribedWord], *, model: str | None = None):
        self.transcription = tuple(words)
        self.model = model

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        model = data.pop("model")
        words = [TranscribedWord(**t) for t in data.pop("words")]
        return cls(words=words, model=model)

    @classmethod
    def from_json(cls, filepath: Path):
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_audition_cue(cls, filepath: Path):
        with open(filepath, encoding="utf-8") as f:
            reader = csv.reader(f, dialect="excel-tab", delimiter="\t")
            next(reader, None)
            rows = list(reader)

        # fields: "Name", "Start", "Duration", "Time Format", "Type", "Description"
        words = [
            TranscribedWord(text=text, start=float(start), end=float(start) + float(duration), confidence=0)
            for (_, start, duration, _, _, text) in rows
        ]

        return cls(words=words)

    @classmethod
    def from_audacity_cue(cls, filepath: Path):
        with open(filepath, encoding="utf-8") as f:
            reader = csv.reader(f, dialect="excel-tab", delimiter="\t")
            rows = list(reader)

        # fields: "Start", "End", "Comment"
        words = [
            TranscribedWord(text=text, start=float(start), end=float(end), confidence=0)
            for (start, end, text) in rows
        ]

        return cls(words=words)

    @classmethod
    def load(cls, filepath: Path, *, mode: str):
        LOAD_MODES = {
            "audio": cls.from_audio,
            "json": cls.from_json,
            "audacity": cls.from_audacity_cue,
            "audition": cls.from_audition_cue
        }

        return LOAD_MODES[mode](filepath)

    @classmethod
    def from_audio(cls, audio_file: Path | str, model_name: str = WHISPER_MODEL, device: str | None = WHISPER_DEVICE):
        """Create a transcription from an audio file using whisper."""
        model = models.load(model_name, device=device)
        result = model.transcribe(str(audio_file), **WHISPER_SETTINGS)

        words = [
            TranscribedWord(text=word.word, start=word.start, end=word.end, confidence=word.probability)
            for segment in result.segments
            for word in segment.words
        ]

        return cls(words=words, model=model_name)

    @property
    def start(self) -> float:
        """Return the time (in seconds) that the first word begins."""
        return self.transcription[0].start

    @property
    def duration(self) -> float:
        """Return the length of time (in seconds) that the transcription lasts."""
        return self.transcription[-1].end

    @property
    def confidence(self) -> float:
        """Return an overall confidence, the mean of all word confidences."""
        return sum(t.confidence for t in self) / len(self)

    @property
    def min_confidence(self) -> float:
        return min(t.confidence for t in self)

    def __iter__(self) -> Iterator[TranscribedWord]:
        return iter(self.transcription)

    def __len__(self) -> int:
        return len(self.transcription)

    def __str__(self) -> str:
        return " ".join(t.text for t in self)

    @property
    def waits(self) -> list[float]:
        """Determine the lengths of pauses after each word."""
        if len(self) < 2:
            return []

        waits: list[float] = []
        for a, b in windowed(self, 2):
            assert a is not None
            assert b is not None
            waits.append(b.start - a.end)

        return waits + [0]  # no wait after last word

    def tabulate(self, *, tablefmt: str = "rounded_grid") -> str:
        """Return a prettified, tabular representation."""
        data = [
            [t.text, t.start, t.end, t.duration, t.confidence]
            for t in self
        ]

        return tabulate(data, headers=["Word", "Start", "End", "Duration", "Confidence"], tablefmt=tablefmt)

    def _export_json(self, filestem: Path, *, suffix: str = ".json") -> None:
        """Export this transcription to file (.json)"""
        data = {
            "model": self.model,
            "text": str(self),
            "words": [asdict(word) for word in self]
        }
        filestem.with_suffix(suffix).write_text(json.dumps(data, indent=4), encoding="utf-8")

    def _export_audacity_cue(self, filestem: Path, *, suffix: str = ".txt") -> None:
        """Export this transcription as Audacity labels."""

        # fields = (start, float) (end, float) (comment, optional str)
        data = [
            [format(word.start, ".6f"), format(word.end, ".6f"), word.text]
            for word in self
        ]

        with open(filestem.with_suffix(suffix), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, dialect="excel-tab", delimiter="\t")
            writer.writerows(data)

    def _export_audition_cue(self, filestem: Path, *, suffix: str = ".csv") -> None:
        """Export this transcription as Audition cues"""
        fields = ["Name", "Start", "Duration", "Time Format", "Type", "Description"]
        data = [
            (f"Marker {i}", seconds_to_hms(word.start), seconds_to_hms(word.duration), "decimal", "Cue", word.text)
            for i, word in enumerate(self, start=1)
        ]

        with open(filestem.with_suffix(suffix), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, dialect="excel-tab")
            writer.writerow(fields)
            writer.writerows(data)

    def export(self, filestem: Path, *, mode: Literal["json", "audacity", "audition"] = "json") -> None:
        """Export this transcription to file"""
        EXPORT_MODES = {
            "json": self._export_json,
            "audacity": self._export_audacity_cue,
            "audition": self._export_audition_cue
        }

        EXPORT_MODES[mode](filestem)
