from collections import defaultdict
from itertools import chain, islice
from pathlib import Path
from stable_whisper.result import WordTiming
import tkinter as tk
from tkinter.filedialog import askopenfilename, askopenfilenames
import ttkbootstrap as ttkb  # type: ignore
from typing import Any, Callable, Generic, Iterable, Iterator, Literal, TypeVar

from stlr.transcribe import Transcription
from stlr.utils import diff_block_str, truncate_path
from stlr.vn import ATLImageGenerator, renpyify


T = TypeVar("T")


class CEntry(ttkb.Entry):
    def __init__(self, master: Any, text: str = "", *args: Any, **kwargs: Any) -> None:
        self._var = tk.StringVar(master, text)
        super().__init__(master, *args, textvariable=self._var, **kwargs)

    @property
    def text(self) -> str:
        return self._var.get()

    @text.setter
    def text(self, text: str) -> None:
        self._var.set(text)


class CDropdown(ttkb.OptionMenu, Generic[T]):
    def __init__(self, master: Any, options: Iterable[T], mapfunc: Callable[[str], T] = str):
        self._var = ttkb.StringVar(master)
        self.options = tuple(str(x) for x in options)
        self.mapfunc = mapfunc
        super().__init__(master, self._var, self.options[0], *self.options)

    @property
    def value(self) -> T:
        return self.mapfunc(self._var.get())

    @value.setter
    def value(self, val: T) -> None:
        self._var.set(str(val))


class CSwitch(ttkb.Checkbutton):
    def __init__(self, master: Any, *args: Any, **kwargs: Any) -> None:
        self._var = tk.IntVar(master)
        super().__init__(master, *args, variable=self._var, **kwargs)

    @property
    def checked(self) -> bool:
        return bool(self._var.get())

    @checked.setter
    def checked(self, value: bool) -> None:
        self._var.set(int(value))


class CText(ttkb.ScrolledText):
    @property
    def text(self) -> str:
        return self.get("1.0", "end-1c")

    @text.setter
    def text(self, text: str) -> None:
        self.delete("1.0", "end")
        self.insert("1.0", text)


def file_selection_row(master: Any, row: int, label_text: str, button_text: str = "Select File", grid_kw: dict[str, Any] | None = None) -> tuple[CEntry, ttkb.Button]:
    def _select_file() -> None:
        entry.text = askopenfilename()

    if grid_kw is None:
        grid_kw = dict()

    ttkb.Label(master, text=label_text).grid(row=row, column=0, **grid_kw)

    entry = CEntry(master, width=80)
    entry.grid(row=row, column=1, **grid_kw)

    button = ttkb.Button(master, text=button_text, command=_select_file)
    button.grid(row=row, column=2, **grid_kw)

    return entry, button


class STLRApp(ttkb.Window):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore
        self.init_components()

    def init_components(self) -> None:
        self.fileselector = ttkb.Button(self, text="Choose Audio Files", command=self.select_files)
        self.fileselector.grid(row=0, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

        self.filenames: list[Path] = []
        self.filename_labels: list[ttkb.Label] = []
        self.transcriptions: list[CEntry] = []

    def clear(self) -> None:
        for widget in chain(self.filename_labels, self.transcriptions):
            widget.grid_remove()

    def select_files(self) -> None:
        self.clear()
        self.filenames = [Path(s) for s in askopenfilenames()]

        if not self.filenames:
            return

        for i, path in enumerate(self.filenames, start=1):
            e = ttkb.Label(self, text=str(path))
            e.grid(row=i, column=0, padx=10, pady=10)
            self.filename_labels.append(e)

            f = CEntry(self, width=150)
            f.grid(row=i, column=1, columnspan=2, sticky="nsew", padx=10, pady=10)
            self.transcriptions.append(f)

        self.transcribe_btn = ttkb.Button(self, text="Transcribe", command=self.transcribe, bootstyle="info")  # type: ignore
        self.transcribe_btn.grid(row=i+1, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)  # type: ignore

    def transcribe(self) -> None:
        for path, entry in zip(self.filenames, self.transcriptions):
            transcription = Transcription.from_audio(path)
            entry.text = renpyify(transcription)


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

class HoshiApp(ttkb.Window):
    WHISPER_STYLE = "primary"
    VOSK_STYLE = "danger"
    MATCHING_STYLE = "success"

    def __init__(self, master: Any, whisper_result: dict[str, Any], vosk_result: list[WordTiming], *args: Any, **kwargs: Any):
        super().__init__(master, *args, **kwargs)
        self.whisper_result = whisper_result
        self.vosk_result = vosk_result

        self.init_components(whisper_text=whisper_result["text"], vosk_text=" ".join(v.word for v in vosk_result))

    def init_components(self, whisper_text: str, vosk_text: str) -> None:
        grid_kw = dict(sticky="nsew", padx=10, pady=10)

        ttkb.Button(self, text="whisper", bootstyle=self.WHISPER_STYLE).grid(row=0, column=0, **grid_kw)
        ttkb.Button(self, text="vosk", bootstyle=self.VOSK_STYLE).grid(row=0, column=1, **grid_kw)

        self.word_parts: dict[Literal["whisper", "vosk", "matching"], list[CEntry]] = {"whisper": [], "vosk": [], "matching": []}

        for i, (whisper_only, vosk_only, matching) in enumerate(diff_block_str(whisper_text, vosk_text), start=1):
            w = CEntry(self, text=whisper_only, width=60, bootstyle=self.WHISPER_STYLE)
            w.grid(row=2*i, column=0, **grid_kw)
            self.word_parts["whisper"].append(w)

            v = CEntry(self, text=vosk_only, width=60, bootstyle=self.VOSK_STYLE)
            v.grid(row=2*i, column=1, **grid_kw)
            self.word_parts["vosk"].append(v)

            m = CEntry(self, text=matching, width=80, bootstyle=self.MATCHING_STYLE)
            m.grid(row=2*i+1, column=0, columnspan=2, **grid_kw)
            self.word_parts["matching"].append(m)

        self.update_button = ttkb.Button(self, text="Update", bootstyle="primary", command=self.update)
        self.update_button.grid(row=2*i+2, column=0, columnspan=3, **grid_kw)

    def _iter_rows(self) -> Iterator[tuple[str, str, str]]:
        for whisper_entry, vosk_entry, matching_entry in zip(self.word_parts["whisper"], self.word_parts["vosk"], self.word_parts["matching"]):
            yield whisper_entry.text, vosk_entry.text, matching_entry.text

    def reconcile(self) -> Iterator[WordTiming]:
        true_transcription = iter(self.whisper_result["text"].split())
        timings = iter(self.vosk_result)

        def _reconcile_one(whisper_phrase: str, vosk_phrase: str) -> Iterator[WordTiming]:
            for whisper_segment, vosk_segment in zip(whisper_phrase.split(" / "), vosk_phrase.split(" / ")):
                n_whisper = len(whisper_segment.split())
                text = ' '.join(islice(true_transcription, n_whisper))
                
                if not (n_vosk := len(vosk_segment.split())):
                    # number of word timings to strip out for this segment
                    continue

                vosk_words = tuple(islice(timings, n_vosk))
                yield WordTiming(word=text, start=vosk_words[0].start, end=vosk_words[-1].end)

        def _reconcile_matching(matching_phrase: str) -> Iterator[WordTiming]:
            for _, word, timing in zip(matching_phrase.split(), true_transcription, timings):
                yield WordTiming(word=word, start=timing.start, end=timing.end)

        for whisper_phrase, vosk_phrase, matching_phrase in self._iter_rows():
            yield from _reconcile_one(whisper_phrase, vosk_phrase)
            yield from _reconcile_matching(matching_phrase)

    def update(self) -> None:
        words = list(self.reconcile())
        self.whisper_result["segments"] = [
            {
                "start": min(w.start for w in words),
                "end": max(w.end for w in words),
                "words": words,
                "text": self.whisper_result["text"]
            }
        ]
        self.destroy()