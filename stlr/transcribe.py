import wave
import stable_whisper
import vosk
import whisper_timestamped
from attrs import define, asdict
import csv
import json
from pathlib import Path
from tabulate import tabulate
import textwrap
from typing import Any, Iterable, Iterator, Literal, Protocol

import stlr.config
import stlr.utils
# from stlr.utils import diff_blocks, pairwise, seconds_to_hms

MODEL_SETTINGS = stlr.config.CONFIG.model
WHISPER_SETTINGS = stlr.config.CONFIG.whisper


@define
class WordTiming:
    word: str
    start: float
    end: float
    confidence: float = 0.0

    @property
    def duration(self) -> float:
        return self.end - self.start


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

    def as_srt(self, *, index: int, wrap_width: int = 40) -> str:
        """Output this segment as an SRT block."""
        text = "\n".join(textwrap.wrap(str(self), width=wrap_width, break_long_words=False))
        start = stlr.utils.seconds_to_hms(self.start, srt_format=True)
        end = stlr.utils.seconds_to_hms(self.end, srt_format=True)
        return f"""\
{index}
{start} --> {end}
{text}
"""


class Transcription:
    def __init__(self, word_timings: Iterable[WordTiming]):
        self.word_timings = tuple(word_timings)

    @classmethod
    def from_dict(cls, data: dict[str, Any]):
        data.pop("model", None)
        word_timings = [WordTiming(**t) for t in data.pop("words")]
        return cls(word_timings=word_timings)

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

        return cls(word_timings=words)

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

        return cls(word_timings=words)

    @classmethod
    def load(cls, filepath: Path, *, mode: Literal["audio", "json", "audacity", "audition"]):
        load_modes = {
            "audio": cls.from_audio,
            "json": cls.from_json,
            "audacity": cls.from_audacity_cue,
            "audition": cls.from_audition_cue
        }

        return load_modes[mode](filepath)

    @classmethod
    def from_audio(cls, audio_file: Path | str, library: str = MODEL_SETTINGS.library, model_name: str = MODEL_SETTINGS.name, device: str | None = MODEL_SETTINGS.device):
        """Create a transcription from an audio file using whisper."""
        model = MODEL_CACHE.get(library, model_name, device)
        return model.transcribe(audio_file)

    @property
    def start(self) -> float:
        """Return the time (in seconds) that the first word begins."""
        try:
            return self.word_timings[0].start
        except IndexError:
            # an empty transcription "starts" at time 0
            return 0.0

    @property
    def duration(self) -> float:
        """Return the length of time (in seconds) that the transcription lasts."""
        try:
            return self.word_timings[-1].end
        except IndexError:
            # an empty transcription has duration 0
            return 0.0

    @property
    def confidence(self) -> float:
        """Return an overall confidence, the mean of all word confidences."""
        return sum((t.confidence or 0.0) for t in self) / len(self)

    @property
    def min_confidence(self) -> float:
        return min((t.confidence or 0.0) for t in self)

    def __iter__(self) -> Iterator[WordTiming]:
        return iter(self.word_timings)

    def __len__(self) -> int:
        return len(self.word_timings)

    def __str__(self) -> str:
        return " ".join(t.word.strip() for t in self)

    def get_segments(self, tolerance: float = 0.0) -> Iterator[Segment]:
        """Group the words into segments of consecutive words without pauses."""
        if len(self) < 2:
            yield Segment(words=list(self), wait_after=0)
            return

        block: list[WordTiming] = [self.word_timings[0]]

        for prev, curr in stlr.utils.pairwise(self):
            wait = curr.start - prev.end
            if wait <= tolerance:
                block.append(curr)
            else:
                yield Segment(words=block, wait_after=wait)
                block = [curr]

        yield Segment(words=block, wait_after=0)

    def get_fragment(self, fragment: str) -> Segment:
        """Determine the timing of a particular fragment of the transcription's text."""
        g = stlr.utils.diff_blocks(self.words, fragment.split())
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
        for a, b in stlr.utils.pairwise(self):
            waits.append(b.start - a.end)

        return waits + [0]  # no wait after last word

    def tabulate(self, *, tablefmt: str = "rounded_grid") -> str:
        """Return a prettified, tabular representation."""
        data = [
            [t.word, t.start, t.end, t.duration, t.confidence]
            for t in self
        ]

        return tabulate(data, headers=["Word", "Start", "End", "Duration", "Confidence"], tablefmt=tablefmt)

    def _export_json(self, filestem: Path, *, suffix: str = ".json") -> None:
        """Export this transcription to file (.json)"""
        data = {
            "text": str(self),
            "words": [asdict(word) for word in self]
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
            (f"Marker {i}", stlr.utils.seconds_to_hms(word.start), stlr.utils.seconds_to_hms(word.duration), "decimal", "Cue", word.word)
            for i, word in enumerate(self, start=1)
        ]

        with open(filestem.with_suffix(suffix), "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, dialect="excel-tab")
            writer.writerow(fields)
            writer.writerows(data)

    def export(self, filestem: Path, *, mode: Literal["json", "audacity", "audition"] = "json") -> None:
        """Export this transcription to file"""
        export_modes = {
            "json": self._export_json,
            "audacity": self._export_audacity_cue,
            "audition": self._export_audition_cue
        }

        export_modes[mode](filestem)

    @staticmethod
    def write_srt(segments: Iterable[Segment], dest: Path) -> None:
        contents = "\n".join(s.as_srt(index=i) for i, s in enumerate(segments, start=1))
        dest.write_text(contents, encoding="utf-8")


class TranscriptionModel(Protocol):
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        ...

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> Transcription:
        ...


class OpenAIWhisper:
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        self.whisper_model = whisper.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> Transcription:
        vosk_model = kwargs.pop("vosk_model", "vosk-model-small-en-us-0.15")
        vosk_result = self.get_vosk_transcription(audio_file, model_name=vosk_model)
        whisper_result: dict[str, Any] = self.whisper_model.transcribe(str(audio_file), **kwargs)  # type: ignore

        return stlr.hoshi.reconcile(whisper_result, vosk_result, mode=stlr.config.CONFIG.hoshi.reconciliation)

    @staticmethod
    def get_vosk_recognizer(audio: wave.Wave_read,
                            model_name: str = stlr.config.CONFIG.vosk.model) -> vosk.KaldiRecognizer:
        model = vosk.Model(model_name=model_name)

        r = vosk.KaldiRecognizer(model, audio.getframerate())
        r.SetMaxAlternatives(10)
        r.SetWords(True)

        return r

    def get_vosk_transcription(self, audio_file: str | Path, model_name: str = stlr.config.CONFIG.vosk.model) -> list[WordTiming]:
        audio = stlr.audio_utils.load_audio(audio_file)
        r = self.get_vosk_recognizer(audio, model_name)

        def process_partial(result: Any) -> list[stlr.transcribe.WordTiming]:
            """Transcribe a section of audio, defined by the result str"""
            data = json.loads(result)
            try:
                words = data["alternatives"][0]["result"]
            except KeyError:
                words: list[dict[str, Any]] = []

            return [stlr.transcribe.WordTiming(word=word["word"], start=word["start"], end=word["end"]) for word in
                    words]

        word_timings: list[stlr.transcribe.WordTiming] = []
        while data := audio.readframes(4096):
            if not r.AcceptWaveform(data):
                continue

            segment = process_partial(r.Result())
            word_timings.extend(segment)

        final_segment = process_partial(r.FinalResult())
        word_timings.extend(final_segment)
        return word_timings


class StableWhisper:
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        self.model = stable_whisper.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> Transcription:
        result = self.model.transcribe(str(audio_file), **kwargs)  # type: ignore

        original_word_timings = [
            w
            for segment in result.segments
            for w in (segment.words or [])  # use "or []" since segment.words might be None instead
        ]

        # convert to our own WordTiming format
        word_timings = [WordTiming(word=x.word, start=x.start, end=x.end) for x in original_word_timings]
        return Transcription(word_timings)


class WhisperTimestamped:
    def __init__(self, name: str, device: str | None = None, download_root: str | None = None, in_memory: bool = False):
        self.model = whisper_timestamped.load_model(name, device, download_root, in_memory)  # type: ignore

    def transcribe(self, audio_file: str | Path, **kwargs: Any) -> stable_whisper.WhisperResult:
        result = whisper_timestamped.transcribe(self.model, str(audio_file), **kwargs)

        word_timings: list[WordTiming] = []
        for segment in result["segments"]:
            for word in segment["words"]:
                # convert this dictionary to a WordTiming and append
                timing = WordTiming(word=word["text"], start=word["start"], end=word["end"], confidence=word["confidence"])
                word_timings.append(timing)

        return Transcription(word_timings)


class ModelCache:
    def __init__(self):
        self.models: dict[tuple[str, str], TranscriptionModel] = dict()

    def get(self, library: str, model_name: str, device: str | None) -> TranscriptionModel:
        lookup = {
            "openai-whisper": OpenAIWhisper,
            "whisper-timestamped": WhisperTimestamped,
            "stable-whisper": StableWhisper
        }

        if library not in lookup:
            raise ValueError(f"invalid library: {library!r}")

        key = (library, model_name)

        if key not in self.models:
            self.models[key] = lookup[library](model_name, device)

        return self.models[key]


MODEL_CACHE = ModelCache()