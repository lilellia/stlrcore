from pathlib import Path
import ttkbootstrap as ttkb
from typing import Any

from stlr.transcribe import Transcription
from stlr.ui import CDropdown, CEntry, CSwitch, CText, file_selection_row
from stlr.utils import truncate_path
from stlr.vn import ATLImageGenerator


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

        self.audio_file_box, self.audio_file_button = file_selection_row(self, row=1, label_text="Data file", grid_kw=grid_kw)
        self.open_mouth_box, self.open_mouth_button = file_selection_row(self, row=2, label_text="Open mouth image", grid_kw=grid_kw)
        self.closed_mouth_box, self.closed_mouth_button = file_selection_row(self, row=3, label_text="Closed mouth image", grid_kw=grid_kw)

        # input file type
        ttkb.Label(self, text="data file type").grid(row=0, column=2, **grid_kw)
        self.ifiletype_selector = CDropdown(self, options=("audio", "json", "audacity cue", "audition cue"))
        self.ifiletype_selector.grid(row=0, column=3, **grid_kw)

        self.annotation_type = CSwitch(self, text="Detailed Annotations", bootstyle="info.RoundToggle.Toolbutton")
        self.annotation_type.grid(row=1, column=3, **grid_kw)

        self.full_image_path = CSwitch(self, text="Full Image Path", bootstyle="info.RoundToggle.Toolbutton")
        self.full_image_path.grid(row=2, column=3, **grid_kw)

        self.let_astral_try = CSwitch(self, text="let astral-chan try ♥", bootstyle="info.RoundToggle.Toolbutton")
        self.let_astral_try.grid(row=3, column=3, **grid_kw)

        self.run_button = ttkb.Button(self, text="Generate ATL image code", command=self._generate_ATL)
        self.run_button.grid(row=7, column=0, columnspan=4, **grid_kw)

        self.atl_box = CText(self, font="TkFixedFont")
        self.atl_box.grid(row=8, column=0, columnspan=4, **grid_kw)

        self.update_annotations_button = ttkb.Button(
            self, text="Update Annotations", command=self._update_annotations,
            # make the button appear purple with cyborg theming
            bootstyle="info"  # type: ignore
        )
        self.update_annotations_button.grid(row=9, column=0, columnspan=4, **grid_kw)

        self.debug_button = ttkb.Button(
            self, text="Show Debug", command=self._show_debug,
            # make the button grey with cyborg (and most others) theming
            bootstyle="secondary")  # type: ignore
        self.debug_button.grid(row=10, column=0, columnspan=4, **grid_kw)

    def _generate_ATL(self) -> None:
        self.atl_box.text = "Generating⋯"
        self.update()

        data_file = Path(self.audio_file_box.text)
        self.transcription = Transcription.load(data_file, mode=self.ifiletype_selector.value)

        open_image = Path(self.open_mouth_box.text)
        if not self.full_image_path.checked:
            open_image = truncate_path(open_image, "images")

        closed_image = Path(self.closed_mouth_box.text)
        if not self.full_image_path.checked:
            closed_image = truncate_path(closed_image, "images")

        self.generator = ATLImageGenerator(
            self.image_name_box.text,
            self.transcription,
            open_image,
            closed_image
        )

        if self.let_astral_try.checked:
            # actually look at the transcription and try to line things up
            self.atl_box.text = self.generator.generate_smart_atl(verbose=self.annotation_type.checked)
        else:
            # just do a naive 0.2 second alternating toggle
            self.atl_box.text = self.generator.generate_atl(verbose=self.annotation_type.checked)

        self.export()
        self.update()

    def _update_annotations(self) -> None:
        open_image = Path(self.open_mouth_box.text)
        if not self.full_image_path.checked:
            open_image = truncate_path(open_image, "images")

        closed_image = Path(self.closed_mouth_box.text)
        if not self.full_image_path.checked:
            closed_image = truncate_path(closed_image, "images")

        self.atl_box.text = self.generator.reannotate(atl=self.atl_box.text, verbose=self.annotation_type.checked)

        self.export()
        self.update()

    def _show_debug(self) -> None:
        grid_kw = dict(sticky="nsew", padx=10, pady=10)

        popup = ttkb.Toplevel("astral (debug)")

        ttkb.Label(popup, text="Transcription:").grid(row=0, column=0, **grid_kw)
        textbox = CText(popup, font="TkFixedFont")
        textbox.text = self.transcription.tabulate()
        textbox.grid(row=1, column=0, **grid_kw)

        popup.mainloop()

    def export(self) -> None:
        """Export the ATL to file."""
        with open(f"ATL-image-{self.image_name_box.text}.txt", "w", encoding="utf-8") as f:
            f.write(self.atl_box.text)
