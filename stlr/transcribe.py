from dataclasses import dataclass, field
from more_itertools import windowed
from pathlib import Path
from tabulate import tabulate
from typing import Iterable, Iterator
import whisper_timestamped as whisper
import yaml


with open(Path(__file__).parent.parent / "config.yaml") as f:
    config = yaml.safe_load(f)

WHISPER_MODEL = config["transcription_models"]["whisper"]
WHISPER_SETTINGS = config["whisper_settings"]


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
    def from_audio(cls, audio_file: Path | str, model_name: str = WHISPER_MODEL):
        """Create a transcription from an audio file using whisper."""
        model = whisper.load_model(model_name)
        data = whisper.transcribe(model, str(audio_file), **WHISPER_SETTINGS)

        words = [
            TranscribedWord(**word)
            for segment in data["segments"]
            for word in segment["words"]
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
