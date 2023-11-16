from attrs import asdict, define
import dataclasses
import csv
import json
from pathlib import Path
from stable_whisper import WhisperResult
from stable_whisper.result import WordTiming
from tabulate import tabulate
from typing import Any, Iterable, Iterator, Literal

from stlr.config import CONFIG
from stlr.models import ModelManager
from stlr.utils import diff_blocks, pairwise, seconds_to_hms

MODEL_SETTINGS = CONFIG.model
WHISPER_SETTINGS = CONFIG.whisper

MODEL_MANAGER = ModelManager()


@define
class Segment:
    words: list[WordTiming]
    wait_after: float

    @property
    def start(self) -> float:
        return min(w.start for w in self.words)

    @property
    def end(self) -> float:
        return max(w.end for w in self.words)

    @property
    def duration(self) -> float:
        return self.end - self.start

    def __iter__(self) -> Iterator[WordTiming]:
        return iter(self.words)

    def __str__(self) -> str:
        return " ".join(w.word.strip() for w in self.words)


class Transcription:
    def __init__(self, words: Iterable[WordTiming], *, model: str | None = None):
        self.transcription = tuple(words)
        self.model = model

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        model = data.pop("model")
        words = [WordTiming(**t) for t in data.pop("words")]
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
            WordTiming(word=word, start=float(start), end=float(start) + float(duration))
            for (_, start, duration, _, _, word) in rows
        ]

        return cls(words=words)

    @classmethod
    def from_audacity_cue(cls, filepath: Path):
        with open(filepath, encoding="utf-8") as f:
            reader = csv.reader(f, dialect="excel-tab", delimiter="\t")
            rows = list(reader)

        # fields: "Start", "End", "Comment"
        words = [
            WordTiming(word=word, start=float(start), end=float(end))
            for (start, end, word) in rows
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
    def from_whisper_result(cls, result: WhisperResult, *, model: str | None = None):
        try:
            words = [w for segment in result.segments for w in segment.words]
        except TypeError:
            # probably using OpenAIWhisper
            words = []

        return cls(
            words=words,
            model=model
        )

    @classmethod
    def from_audio(cls, audio_file: Path | str, library: str = MODEL_SETTINGS.library, model_name: str = MODEL_SETTINGS.name, device: str | None = MODEL_SETTINGS.device):
        """Create a transcription from an audio file using whisper."""
        model = MODEL_MANAGER.get(library, model_name, device)
        result = model.transcribe(audio_file)
        return cls.from_whisper_result(result, model=model_name)

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
        return sum((t.probability or 0.0) for t in self) / len(self)

    @property
    def min_confidence(self) -> float:
        return min((t.probability or 0.0) for t in self)

    def __iter__(self) -> Iterator[WordTiming]:
        return iter(self.transcription)

    def __len__(self) -> int:
        return len(self.transcription)

    def __str__(self) -> str:
        return " ".join(t.word.strip() for t in self)

    def get_segments(self, tolerance: float = 0.0) -> Iterator[Segment]:
        """Group the words into segments of consecutive words without pauses."""
        if len(self) < 2:
            yield Segment(words=list(self), wait_after=0)
            return

        block: list[WordTiming] = [self.transcription[0]]

        for prev, curr in pairwise(self):
            wait = curr.start - prev.end
            if wait <= tolerance:
                block.append(curr)
            else:
                yield Segment(words=block, wait_after=wait)
                block = [curr]

        yield Segment(words=block, wait_after=0)

    def get_fragment(self, fragment: str) -> Segment:
        """Determine the timing of a particular fragment of the transcription's text."""
        g = diff_blocks(self.words, fragment.split())
        head, _, match = next(g)
        i = len(head)
        n = len(match)

        return Segment(words=list(self)[i:i+n], wait_after=0)

    @property
    def words(self) -> list[str]:
        return [w.word.strip() for w in self]

    @property
    def waits(self) -> list[float]:
        """Determine the lengths of pauses after each word."""
        if len(self) < 2:
            return []

        waits: list[float] = []
        for a, b in pairwise(self):
            waits.append(b.start - a.end)

        return waits + [0]  # no wait after last word

    def tabulate(self, *, tablefmt: str = "rounded_grid") -> str:
        """Return a prettified, tabular representation."""
        data = [
            [t.word, t.start, t.end, t.duration, t.probability]
            for t in self
        ]

        return tabulate(data, headers=["Word", "Start", "End", "Duration", "Confidence"], tablefmt=tablefmt)

    def _export_json(self, filestem: Path, *, suffix: str = ".json") -> None:
        """Export this transcription to file (.json)"""
        data = {
            "model": self.model,
            "text": str(self),
            "words": [dataclasses.asdict(word) for word in self]
        }
        filestem.with_suffix(suffix).write_text(json.dumps(data, indent=4), encoding="utf-8")

    def _export_audacity_cue(self, filestem: Path, *, suffix: str = ".txt") -> None:
        """Export this transcription as Audacity labels."""

        # fields = (start, float) (end, float) (comment, optional str)
        data = [
            [format(word.start, ".6f"), format(word.end, ".6f"), word.word]
            for word in self
        ]

        with open(filestem.with_suffix(suffix), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, dialect="excel-tab", delimiter="\t")
            writer.writerows(data)

    def _export_audition_cue(self, filestem: Path, *, suffix: str = ".csv") -> None:
        """Export this transcription as Audition cues"""
        fields = ["Name", "Start", "Duration", "Time Format", "Type", "Description"]
        data = [
            (f"Marker {i}", seconds_to_hms(word.start), seconds_to_hms(word.duration), "decimal", "Cue", word.word)
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
