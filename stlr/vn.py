from itertools import cycle
from pathlib import Path

from stlr.transcribe import TranscribedWord, Transcription
from stlr.utils import frange, get_space_prefix, read_leading_float


def wait_tag(seconds: float, *, precision: int = 2) -> str:
    """Construct a Ren'Py wait tag: {w=...}"""
    seconds = round(seconds, precision)

    return f"{{w={seconds}}}" if seconds else ""


def renpyify(transcription: Transcription) -> str:
    """Convert the list of transcribed words into a Ren'Py say statement."""
    waits = transcription.waits
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
        return sum(read_leading_float(line) or 0.0 for line in self.atl.splitlines())

    def annotate(self, start: float, end: float, *, verbose: bool = True) -> str:
        boundaries = sorted([(t.word, t.end, "end") for t in self.transcription if start <= t.end <= end], key=lambda item: item[1])

        if not verbose:
            # just get word endings
            a = ', '.join(word for word, _, _ in boundaries)
            return f"  # {a}" if boundaries else ""

        # otherwise, we need the detailed annotation, so...
        boundaries += [(t.word, t.start, "start") for t in self.transcription if start <= t.start <= end]
        boundaries.sort(key=lambda item: item[1])

        annotation = f"  # animation time: {start:.3f} → {end:.3f} "
        annotation += ' '.join(f"| {word!r} [{bound} @ {time:.2f}]" for word, time, bound in boundaries)

        return annotation.rstrip()

    def alternate_frames_for_duration(
            self,
            duration: float, start: float, time_step: float = 0.2,
            *, ensure_close: bool = True, verbose: bool = True
    ) -> tuple[list[str], Path | None]:
        """Alternate open/closed frames for *at least* the given duration, returning the new lines and the last image used."""
        lines: list[str] = []
        image: Path | None = None

        for time, image in zip(frange(start, start+duration, time_step), self._images):
            lines.append(f"    \"{image.as_posix()}\"")

            annotation = self.annotate(time, time + time_step, verbose=verbose)
            delay_line = f"    {time_step:.3f}{annotation}"
            lines.append(delay_line)

        if ensure_close and image != self.closed_mouth:
            lines.append(f"    \"{next(self._images).as_posix()}\"")

        return lines, image

    def generate_atl(self, *, verbose: bool = True) -> str:
        lines = [
            f"image {self.image_name}:",
            f"    # {'' if self.transcription.confident else '(!)'} Transcription: {self.transcription}",
            f"    # length: {self.transcription.duration:.3f} seconds"
        ]

        added_lines, _ = self.alternate_frames_for_duration(
            duration=self.transcription.duration,
            start=0, time_step=0.2,
            ensure_close=True, verbose=verbose
        )
        lines.extend(added_lines)

        self._atl = "\n".join(lines)
        return self._atl

    def _generate_smart_block(self, word: TranscribedWord, target_frame_time: float = 0.2, *, verbose: bool = True) -> list[str]:
        lines: list[str] = []

        # The actual length (in seconds) of each frame.
        #                               ↓ the "actual" number of frames, as close to target number
        frame_length = word.duration / round(word.duration / target_frame_time)
        lines, _ = self.alternate_frames_for_duration(
            duration=word.duration, start=word.start, time_step=frame_length,
            ensure_close=True, verbose=verbose
        )

        return lines

    def generate_smart_atl(self, *, verbose: bool = True) -> str:
        lines = [
            f"image {self.image_name}:",
            f"    # {'' if self.transcription.confident else '(!)'} Transcription: {self.transcription}",
            f"    # length: {self.transcription.duration:.2f} seconds",
            f"    {self.closed_mouth.as_posix()}",
            f"    {self.transcription.start}"
        ]

        for word, wait in zip(self.transcription, self.transcription.waits):
            lines.extend(self._generate_smart_block(word, verbose=verbose))
            if wait:
                lines.append(f"    {wait:.3f}")

        return "\n".join(lines)

    def reannotate(self, atl: str, *, verbose: bool = True) -> str:
        lines: list[str] = []

        time = 0.0
        for line in atl.splitlines():
            if (pause := read_leading_float(line)) is None:
                # this line doesn't have a delay, so add it unchanged
                lines.append(line)
                continue

            prefix = get_space_prefix(line)
            annotation = self.annotate(time, time + pause, verbose=verbose)
            lines.append(f"{prefix}{pause:.2f}{annotation}")

            time += pause

            if time >= self.transcription.duration:
                # we've reached the end of the line, so we can cut the animation here
                break
        else:
            # we're exhausted the existing animation,
            # so check if we need to add additional frames
            if time < self.transcription.duration:
                buffer = self.transcription.duration - time
                added_lines, _ = self.alternate_frames_for_duration(
                    duration=buffer, start=time, ensure_close=True, verbose=verbose
                )
                lines.extend(added_lines)

        return "\n".join(lines)
