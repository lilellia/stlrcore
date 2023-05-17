from stlr.transcribe import Transcription


def wait_tag(seconds: float, *, precision: int = 2) -> str:
    """Construct a Ren'Py wait tag: {w=...}"""
    seconds = round(seconds, precision)

    return f"{{w={seconds}}}" if seconds else ""


def renpyify(transcription: Transcription) -> str:
    """Convert the list of transcribed words into a Ren'Py say statement."""
    waits = transcription.waits() + [0]  # no additional wait after final word
    return " ".join(
        f"{word.word}{wait_tag(wait)}"
        for word, wait in zip(transcription, waits)
    )
