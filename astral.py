from itertools import cycle
from pathlib import Path
import ttkbootstrap as ttkb  # type: ignore
import re
from typing import Any

from stlr.transcribe import Transcription, transcribe
from stlr.ui import CEntry, CText, file_selection_row
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

        self.run_button = ttkb.Button(self, text="Generate ATL image code", command=self._generate_ATL)
        self.run_button.grid(row=4, column=0, columnspan=3, **grid_kw)

        self.atl_box = CText(self)
        self.atl_box.grid(row=5, column=0, columnspan=3, **grid_kw)

        self.update_annotations_button = ttkb.Button(
            self, text="Update Annotations", command=self._update_annotations,
            # make the button appear purple with cyborg theming
            bootstyle="info"  # type: ignore
        )
        self.update_annotations_button.grid(row=6, column=0, columnspan=3, **grid_kw)

    def _generate_ATL(self) -> None:
        self.atl_box.text = "Generating⋯"
        self.update()

        self.transcription = transcribe(Path(self.audio_file_box.text))

        self.atl_box.text = alternate_frames(
            self.transcription,
            atl_name=self.image_name_box.text,
            open_image=Path(self.open_mouth_box.text),
            closed_image=Path(self.closed_mouth_box.text)
        )

        self.update()

    def _update_annotations(self) -> None:
        self.atl_box.text = update_annotations(
            self.transcription, atl=self.atl_box.text,
            open_image=Path(self.open_mouth_box.text),
            closed_image=Path(self.closed_mouth_box.text)
        )


def word_boundaries_in_range(transcription: Transcription, range_start: float, range_end: float) -> str:
    """Find word boundaries from the transcription in the given range of time, converting them to annotation format."""
    word_starts = [t for t in transcription if range_start <= t.start < range_end]
    word_ends = [t for t in transcription if range_start <= t.end < range_end]

    result = ""

    if word_ends:
        t = word_ends[0]
        result += f" :: INCLUDES END-OF-WORD: {t.word!r} (ends @ {t.end:.2f})"

    if word_starts:
        t = word_starts[0]
        result += f" :: INCLUDES START-OF-WORD: {t.word!r} (starts @ {t.start:.2f})"

    return result


def alternate_frames_for_duration(
        duration: float, start_time: float, transcription: Transcription,
        open_image: Path, closed_image: Path,
        time_step: float = 0.2
) -> tuple[list[str], Path]:
    images = cycle([open_image, closed_image])
    lines: list[str] = []

    for time, img in zip(arange(start=start_time, stop=start_time+duration, step=time_step), images):
        lines.append(f"    \"{img}\"")

        word_annotations = word_boundaries_in_range(transcription, time, time + time_step)
        delay_line = f"    {time_step:.2f}  # animation time: {time:.2f} → {time + time_step:.2f}{word_annotations}"
        lines.append(delay_line)

    return lines, img  # type: ignore


def alternate_frames(transcription: Transcription, atl_name: str, open_image: Path, closed_image: Path, time_step: float = 0.2) -> str:
    lines: list[str] = [
        f"# Transcription: {transcription}",
        f"# length: {transcription.duration:.2f} s"
        f"image {atl_name}:"
    ]

    added_lines, last_img = alternate_frames_for_duration(
        duration=transcription.duration, start_time=0, transcription=transcription,
        open_image=open_image, closed_image=closed_image,
        time_step=time_step
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


def update_annotations(transcription: Transcription, atl: str, open_image: Path, closed_image: Path, time_step: float = 0.2) -> str:
    original_lines = atl.splitlines()
    new_lines: list[str] = []

    frame_time = 0
    for line in original_lines:
        if (match := re.match(r"(\s*)([0-9]*\.?[0-9]+)", line)):
            prefix = match.group(1)
            pause = float(match.group(2))

            word_annotations = word_boundaries_in_range(transcription, frame_time, frame_time + pause)
            annotation = f"  # animation time: {frame_time:.2f} → {frame_time + pause:.2f}{word_annotations}"
            new_lines.append(f"{prefix}{pause:.2f}{annotation}")

            frame_time += pause

            if frame_time >= transcription.duration:
                # we've reached the end of the line, so we can cut the animation here
                print("--- CUT ANIMATION ---")
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
