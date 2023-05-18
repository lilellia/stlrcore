from itertools import cycle
from pathlib import Path
import re

from stlr.transcribe import Transcription
from stlr.utils import frange


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


class ATLImageGenerator:
    def __init__(self, image_name: str, transcription: Transcription, open_mouth: Path, closed_mouth: Path):
        self.image_name = image_name
        self.transcription = transcription
        self.open_mouth = open_mouth
        self.closed_mouth = closed_mouth
        self._images = cycle([self.open_mouth, self.closed_mouth])
        self._atl = ""

    @property
    def atl(self) -> str:
        """Return the generated image ATL code."""
        return self._atl

    @property
    def duration(self) -> float:
        """Determine the length (in seconds) of the animation."""
        result = 0.0

        for line in self.atl.splitlines():
            if match := re.match(r"\s*([0-9]*\.?[0-9]+)", line):
                result += float(match.group(1))

        return result

    def annotate(self, start: float, end: float, *, verbose: bool = True) -> str:
        boundaries = sorted([(t.word, t.end, "end") for t in self.transcription if start <= t.end < end], key=lambda item: item[1])

        if not verbose:
            # just get word endings
            a = ', '.join(word for word, _, _ in boundaries)
            return f"  # {a}" if boundaries else ""

        # otherwise, we need the detailed annotation, so...
        boundaries += [(t.word, t.start, "start") for t in self.transcription if start <= t.start < end]
        boundaries.sort(key=lambda item: item[1])

        annotation = f"  # animation time: {start:.2f} → {end:.2f} "
        annotation += ' '.join(f"| {word!r} [{bound} @ {time:.2f}]" for word, time, bound in boundaries)

        return annotation.rstrip()

    def alternate_frames_for_duration_ge(
            self,
            duration: float, start: float, time_step: float = 0.2,
            *, ensure_close: bool = True, verbose: bool = True
    ) -> tuple[list[str], Path | None]:
        """Alternate open/closed frames for *at least* the given duration, returning the new lines and the last image used."""
        lines: list[str] = []
        image: Path | None = None

        for time, image in zip(frange(start, start+duration, time_step), self._images):
            lines.append(f"    \"{image}\"")

            annotation = self.annotate(time, time + time_step, verbose=verbose)
            delay_line = f"    {time_step:.2f}{annotation}"
            lines.append(delay_line)

        if ensure_close and image != self.closed_mouth:
            lines.append(f"    \"{next(self._images)}\"")

        return lines, image

    def generate_atl(self, *, verbose: bool = True) -> str:
        lines = [
            f"image {self.image_name}:",
            f"    # {'' if self.transcription.confident else '(!)'} Transcription: {self.transcription}",
            f"    # length: {self.transcription.duration:.2f} seconds"
        ]

        added_lines, _ = self.alternate_frames_for_duration_ge(
            duration=self.transcription.duration,
            start=0, time_step=0.2,
            ensure_close=True, verbose=verbose
        )
        lines.extend(added_lines)

        self._atl = "\n".join(lines)
        return self._atl
