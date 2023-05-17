from dataclasses import dataclass
import json
from loguru import logger
from more_itertools import windowed
from pathlib import Path
from typing import Any, Iterable, Iterator
import whisper  # type: ignore

from stlr.audio import load_audio, build_recognizer


@dataclass
class TranscribedWord:
    word: str
    start: float
    end: float

    @property
    def duration(self) -> float:
        """Return the length of time the word is spoken."""
        return self.end - self.start

    def __str__(self) -> str:
        return f"{self.word}({self.start}-{self.end}/{self.duration:.3f})"


class Transcription:
    def __init__(self, words: Iterable[TranscribedWord]):
        self._transcription = tuple(words)

    @property
    def duration(self) -> float:
        """Return the length of time (in seconds) that the transcription lasts."""
        return self._transcription[-1].end

    def __iter__(self) -> Iterator[TranscribedWord]:
        return iter(self._transcription)

    def __len__(self) -> int:
        return len(self._transcription)

    def __str__(self) -> str:
        return " ".join(t.word for t in self)

    def waits(self) -> list[float]:
        """Determine the lengths of pauses between words."""
        if len(self) < 2:
            return []

        waits: list[float] = []
        for a, b in windowed(self, 2):
            assert a is not None
            assert b is not None
            waits.append(b.start - a.end)

        return waits


def _transcribe_partial(result: Any) -> list[TranscribedWord]:
    """Transcribe a section of audio, as defined by the Result str."""
    data = json.loads(result)
    guess: list[dict[str, Any]] = data["alternatives"][0].get("result", [])

    return [TranscribedWord(**w) for w in guess]


def _transcribe_vosk(audio_file: Path, language: str = "en-us") -> Transcription:
    """Transcribe an audio file in the given language while providing timing information."""
    audio = load_audio(audio_file)
    recognizer = build_recognizer(audio, language)

    words: list[TranscribedWord] = []
    while (data := audio.readframes(4000)):
        if not recognizer.AcceptWaveform(data):  # type: ignore
            continue

        words += _transcribe_partial(recognizer.Result())

    return Transcription(words + _transcribe_partial(recognizer.FinalResult()))


def _transcribe_whisper(audio_file: Path) -> list[str]:
    """Accurately transcribe an audio file."""
    model = whisper.load_model("base")
    return model.transcribe(str(audio_file))["text"].split()  # type: ignore


def transcribe(audio_file: Path, language: str = "en-us") -> Transcription:
    """Transcribe an audio file in the given language."""
    timed = _transcribe_vosk(audio_file, language)
    untimed = _transcribe_whisper(audio_file)

    if len(timed) != len(untimed):
        logger.warning(f"   vosk: [{len(timed)}] {' '.join(s.word for s in timed)}")
        logger.warning(f"whisper: [{len(untimed)}] {' '.join(untimed)}")
        logger.error(f"cannot transcribe file {audio_file}: transcriptions do not match")
        return Transcription([])

    # If they have the same length, assume that the untimed (whisper) transcription is correct.
    return Transcription(TranscribedWord(w, v.start, v.end) for v, w in zip(timed, untimed))
