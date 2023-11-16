from argparse import ArgumentParser
from pathlib import Path
import ttkbootstrap as ttkb
from typing import Any
import tkinter.font
from typing import NamedTuple

from stlr.config import CONFIG
from stlr.transcribe import Transcription
from stlr.ui import CCombobox, CEntry, CText, CToplevel, file_selection_row
from stlr.utils import seconds_to_hms


def get_system_fonts() -> list[str]:
    """Return a list of all fonts on the system."""
    return sorted(tkinter.font.families())


class SimpleSegment(NamedTuple):
    text: str
    start: float
    end: float


class SubtitleGenerator(ttkb.Window):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.init_components()

    def init_components(self) -> None:
        grid_kw = dict(sticky="nsew", padx=10, pady=10)

        # audio file input
        self.audio_file_box, self.audio_file_button = file_selection_row(self, row=0, label_text="Audio File", grid_kw=grid_kw)

        # font selector
        ttkb.Label(self, text="Subtitle Font").grid(row=1, column=0, **grid_kw)
        self.font_selector = CCombobox(self, get_system_fonts())
        self.font_selector.grid(row=1, column=1, **grid_kw)

        # font size selector
        ttkb.Label(self, text="Font Size (pt)").grid(row=2, column=0, **grid_kw)
        self.fontsize_selector = CEntry(self)
        self.fontsize_selector.grid(row=2, column=1, **grid_kw)

        # image size
        ttkb.Label(self, text="Image Size (width, height)").grid(row=3, column=0, **grid_kw)
        self.image_size_box = CEntry(self)
        self.image_size_box.grid(row=3, column=1, **grid_kw)

        # subregion
        ttkb.Label(self, text="Subtitle Region (x, y, width, height)").grid(row=4, column=0, **grid_kw)
        self.image_size_box = CEntry(self)
        self.image_size_box.grid(row=4, column=1, **grid_kw)

        # generate transcription
        self.generate_button = ttkb.Button(
            self,
            text="Generate Subtitles",
            command=self.create_subtitles,
            bootstyle="info"  # type: ignore
        )
        self.generate_button.grid(row=5, column=0, columnspan=3, **grid_kw)

        # transcription box
        self.transcription_box = CText(self, font="TkFixedFont")
        self.transcription_box.grid(row=7, column=0, columnspan=3, **grid_kw)

    def create_subtitles(self) -> None:
        # Step 1: Generate the transcription
        self._generate_transcription()

        # Step 2: Have the user divide the transcription into the desired segments.
        segments = self._create_segments()
        self.transcription_box.text = "\n".join(f"[{s.start}-{s.end}] {s.text}" for s in segments)
        self.update()

        # Step 3: Have the user correct spelling, punctuation, etc.
        segments = self._correct_segments(segments)
        self.transcription_box.text = "\n".join(f"[{s.start}-{s.end}] {s.text}" for s in segments)
        self.update()

        # Step 4: create srt file
        self._generate_srt(segments)

    def _generate_transcription(self) -> None:
        self.transcription_box.text = "Generating transcription⋯"
        self.update()

        data_file = Path(self.audio_file_box.text)
        self.transcription = Transcription.from_audio(data_file)

        self.transcription_box.text = str(self.transcription)
        self.update()

    def _create_segments(self) -> list[SimpleSegment]:
        grid_kw = dict(sticky="nsew", padx=10, pady=10)
        window: CToplevel[list[SimpleSegment]] = CToplevel("Create Segments")

        ttkb.Label(window, text="Split the transcription into 'segments', one per line.") \
            .grid(row=0, column=0, **grid_kw)

        textbox = CText(window)
        textbox.text = str(self.transcription)
        textbox.grid(row=1, column=0, **grid_kw)

        def _read_segments() -> None:
            fragments = textbox.text.splitlines()
            segments = [self.transcription.get_fragment(f) for f in fragments]
            window._result = [SimpleSegment(str(s), s.start, s.end) for s in segments]  # type: ignore
            window.destroy()

        ttkb.Button(
            window,
            text="Create Segments",
            command=_read_segments
        ).grid(row=2, column=0, **grid_kw)

        # window.result may return None. Map that to no segments.
        return window.result() or []

    def _correct_segments(self, segments: list[SimpleSegment]) -> list[SimpleSegment]:
        grid_kw = dict(sticky="nsew", padx=10, pady=10)
        window: CToplevel[list[SimpleSegment]] = CToplevel("Create Segments")

        ttkb.Label(window, text="Correct spelling, punctuation, etc. for each segment.") \
            .grid(row=0, column=0, **grid_kw)

        textbox = CText(window)
        textbox.text = "\n".join(s.text for s in segments)
        textbox.grid(row=1, column=0, **grid_kw)

        def _read_segments() -> None:
            window._result = [  # type: ignore
                SimpleSegment(line, segment.start, segment.end)
                for line, segment in zip(textbox.text.splitlines(), segments)
            ]
            window.destroy()

        ttkb.Button(
            window,
            text="Correct Segments",
            command=_read_segments
        ).grid(row=2, column=0, **grid_kw)

        # window.result may return None. Map that to no segments.
        return window.result() or []

    def _generate_srt(self, segments: list[SimpleSegment]) -> None:
        contents = ""
        for i, segment in enumerate(segments, start=1):
            start = seconds_to_hms(segment.start, omit_hour=False).replace(".", ",")
            end = seconds_to_hms(segment.end, omit_hour=False).replace(".", ",")
            contents += f"""
{i}
{start} --> {end}
{segment.text}

"""

        with open("subtitles.srt", "w+", encoding="utf-8") as f:
            f.write(contents)


if __name__ == "__main__":
    SubtitleGenerator("Σελήνη (Selene)", themename="vapor").mainloop()
