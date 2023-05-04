from pathlib import Path
from more_itertools import windowed

from stlr.transcribe import TranscribedWord, transcribe


def wait_tag(seconds: float, *, precision: int = 2) -> str:
    """Construct a Ren'Py wait tag: {w=...}"""
    seconds = round(seconds, precision)

    return f"{{w={seconds}}}" if seconds else ""


def get_waits(words: list[TranscribedWord]) -> list[float]:
    """Determine the lengths of pauses in between words."""
    if len(words) < 2:
        return []

    waits: list[float] = []
    for a, b in windowed(words, 2):
        assert a is not None
        assert b is not None
        waits.append(b.start - a.end)

    return waits


def transcribe_with_pauses(correct_transcription: str, audio_file: Path, language: str = "en-us") -> str:
    """Transcribe the given audio in the given language, formatting as a Ren'Py say statement."""
    words = transcribe(audio_file, language)

    if len(words) != len(correct_transcription.split()):
        transcription = " ".join(w.word for w in words)
        raise ValueError(
            f"generated transcription ({transcription}) and correct "
            f"transcription ({correct_transcription}) do not match number of words"
        )

    correct_words = correct_transcription.split()
    waits = get_waits(words)
    return " ".join(
        f"{word}{wait_tag(wait)}"
        for word, wait in zip(correct_words, waits)
    )
