from itertools import cycle
from pathlib import Path
import ttkbootstrap as ttkb  # type: ignore
import re
from typing import Any

from stlr.transcribe import Transcription, transcribe
from stlr.ui import CEntry, CSwitch, CText, file_selection_row
from stlr.utils import arange


class AstralApp(ttkb.Window):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.init_components()

    def init_components(self) -> None:
        grid_kw = dict(sticky="nsew", padx=10, pady=10)

        # ATL image name
        ttkb.Label(self, text="ATL image name").grid(row=0, column=0, **grid_kw)
        self.image_name_box = CEntry(self)
        self.image_name_box.grid(row=0, column=1, **grid_kw)

        self.audio_file_box, self.audio_file_button = file_selection_row(self, row=1, label_text="Audio file", grid_kw=grid_kw)
        self.open_mouth_box, self.open_mouth_button = file_selection_row(self, row=2, label_text="Open mouth image", grid_kw=grid_kw)
        self.closed_mouth_box, self.closed_mouth_button = file_selection_row(self, row=3, label_text="Closed mouth image", grid_kw=grid_kw)

        self.annotation_type = CSwitch(self, text="Detailed Annotations", bootstyle="info.RoundToggle.Toolbutton")
        self.annotation_type.grid(row=4, column=2, **grid_kw)

        self.full_image_path = CSwitch(self, text="Full Image Path", bootstyle="info.RoundToggle.Toolbutton")
        self.full_image_path.grid(row=5, column=2, **grid_kw)

        self.run_button = ttkb.Button(self, text="Generate ATL image code", command=self._generate_ATL)
        self.run_button.grid(row=6, column=0, columnspan=3, **grid_kw)

        self.atl_box = CText(self)
        self.atl_box.grid(row=7, column=0, columnspan=3, **grid_kw)

        self.update_annotations_button = ttkb.Button(
            self, text="Update Annotations", command=self._update_annotations,
            # make the button appear purple with cyborg theming
            bootstyle="info"  # type: ignore
        )
        self.update_annotations_button.grid(row=8, column=0, columnspan=3, **grid_kw)

    def _generate_ATL(self) -> None:
        self.atl_box.text = "Generating⋯"
        self.update()

        self.transcription = transcribe(Path(self.audio_file_box.text))

        open_image = Path(self.open_mouth_box.text)
        if not self.full_image_path.checked:
            open_image = truncate_path(open_image, "images")

        closed_image = Path(self.closed_mouth_box.text)
        if not self.full_image_path.checked:
            closed_image = truncate_path(closed_image, "images")

        self.atl_box.text = alternate_frames(
            self.transcription,
            atl_name=self.image_name_box.text,
            open_image=open_image,
            closed_image=closed_image,
            verbose=self.annotation_type.checked
        )

        self.export()
        self.update()

    def _update_annotations(self) -> None:
        open_image = Path(self.open_mouth_box.text)
        if not self.full_image_path.checked:
            open_image = truncate_path(open_image, "images")

        closed_image = Path(self.closed_mouth_box.text)
        if not self.full_image_path.checked:
            closed_image = truncate_path(closed_image, "images")

        self.atl_box.text = update_annotations(
            self.transcription, atl=self.atl_box.text,
            open_image=open_image,
            closed_image=closed_image,
            verbose=self.annotation_type.checked
        )

        self.export()
        self.update()

    def export(self) -> None:
        """Export the ATL to file."""
        with open(f"ATL-image-{self.image_name_box.text}.txt", "w") as f:
            f.write(self.atl_box.text)


def truncate_path(path: Path, highest_parent: str) -> Path:
    if match := re.search(rf"({highest_parent}.*)", str(path)):
        return Path(match.group(1))

    raise ValueError(f"cannot truncate {path} to {highest_parent}")


def word_boundaries_in_range(transcription: Transcription, range_start: float, range_end: float) -> list[tuple[str, float, str]]:
    """Find word boundaries from the transcription in the given range of time, converting them to annotation format."""
    word_starts = [t for t in transcription if range_start <= t.start < range_end]
    word_ends = [t for t in transcription if range_start <= t.end < range_end]

    return [(t.word, t.end, "end") for t in word_ends] + [(t.word, t.end, "start") for t in word_starts]


def create_annotation(transcription: Transcription, frame_start: float, frame_end: float, *, verbose: bool) -> str:
    boundaries = word_boundaries_in_range(transcription, frame_start, frame_end)

    if not verbose:
        # just get word endings
        endings = [word for word, _, boundary in boundaries if boundary == "end"]
        return f"  # {' '.join(endings)}" if endings else ""

    # otherwise, we need the detailed annotation, so...
    annotation = f"  # animation time: {frame_start:.2f} → {frame_end:.2f} "

    boundaries.sort(key=lambda item: item[1])  # sorted by time

    annotation += ' '.join(f"| {word!r} [{bound} @ {time:.2f}]" for word, time, bound in boundaries)

    return annotation.rstrip()


def alternate_frames_for_duration(
        duration: float, start_time: float, transcription: Transcription,
        open_image: Path, closed_image: Path,
        time_step: float = 0.2,
        verbose: bool = True
) -> tuple[list[str], Path]:
    images = cycle([open_image, closed_image])
    lines: list[str] = []

    for time, img in zip(arange(start=start_time, stop=start_time+duration, step=time_step), images):
        lines.append(f"    \"{img}\"")

        annotation = create_annotation(transcription, time, time + time_step, verbose=verbose)
        delay_line = f"    {time_step:.2f}{annotation}"
        lines.append(delay_line)

    return lines, img  # type: ignore


def alternate_frames(transcription: Transcription, atl_name: str, open_image: Path, closed_image: Path, time_step: float = 0.2, verbose: bool = True) -> str:
    lines: list[str] = [
        f"# {'' if transcription.confident else ' ∗'} Transcription: {transcription}",
        f"# length: {transcription.duration:.2f} s",
        f"image {atl_name}:"
    ]

    added_lines, last_img = alternate_frames_for_duration(
        duration=transcription.duration, start_time=0, transcription=transcription,
        open_image=open_image, closed_image=closed_image,
        time_step=time_step, verbose=verbose
    )

    lines.extend(added_lines)

    # ensure that the animation ends with a closed mouth
    if last_img != closed_image:
        lines.append(f"    \"{closed_image}\"")

    return "\n".join(lines)


def get_animation_duration(atl: str) -> float:
    duration = 0.0

    for line in atl.splitlines():
        if (match := re.match(r"\s*([0-9]*\.?[0-9]+)", line)):
            duration += float(match.group(1))

    return duration


def update_annotations(transcription: Transcription, atl: str, open_image: Path, closed_image: Path, time_step: float = 0.2, verbose: bool = True) -> str:
    original_lines = atl.splitlines()
    new_lines: list[str] = []

    frame_time = 0
    for line in original_lines:
        if (match := re.match(r"(\s*)([0-9]*\.?[0-9]+)", line)):
            prefix = match.group(1)
            pause = float(match.group(2))

            annotation = create_annotation(transcription, frame_time, frame_time + pause, verbose=verbose)
            new_lines.append(f"{prefix}{pause:.2f}{annotation}")

            frame_time += pause

            if frame_time >= transcription.duration:
                # we've reached the end of the line, so we can cut the animation here
                break
        else:
            # doesn't have a pause, so just add unchanged
            new_lines.append(line)
    else:
        # we exhausted the existing animation, so check if we need to add additional frames
        if frame_time < transcription.duration:
            buffer = transcription.duration - frame_time
            added_lines, last_image = alternate_frames_for_duration(
                buffer, frame_time, transcription=transcription,
                open_image=open_image, closed_image=closed_image,
                time_step=time_step
            )

            new_lines.extend(added_lines)

            # ensure the animation once again ends in closed mouth
            if last_image != closed_image:
                new_lines.append(f"    \"{closed_image}\"")

    return "\n".join(new_lines)


def main():
    AstralApp("astral", themename="cyborg").mainloop()


if __name__ == "__main__":
    main()
