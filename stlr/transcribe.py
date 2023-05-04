from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

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


def _transcribe_partial(result: Any) -> list[TranscribedWord]:
    """Transcribe a section of audio, as defined by the Result str."""
    data = json.loads(result)
    guess: list[dict[str, Any]] = data["alternatives"][0]["result"]

    return [TranscribedWord(**w) for w in guess]


def transcribe(audio_file: Path, language: str = "en-us") -> list[TranscribedWord]:
    """Transcribe an audio file in the given language."""
    audio = load_audio(audio_file)
    recognizer = build_recognizer(audio, language)

    words: list[TranscribedWord] = []
    while (data := audio.readframes(4000)):
        if not recognizer.AcceptWaveform(data):  # type: ignore
            continue

        words += _transcribe_partial(recognizer.Result())

    return words + _transcribe_partial(recognizer.FinalResult())


def transcribe_to_string(audio_file: Path, language: str = "en-us") -> str:
    """Transcribe an audio file in the given language."""
    words = transcribe(audio_file, language)
    return " ".join(w.word for w in words)
