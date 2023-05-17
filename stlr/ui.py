from itertools import chain
from pathlib import Path
import tkinter as tk
from tkinter.filedialog import askopenfilename, askopenfilenames
import ttkbootstrap as ttkb  # type: ignore
from typing import Any

from stlr.transcribe import transcribe
from stlr.vn import renpyify


class CEntry(ttkb.Entry):
    def __init__(self, master: Any, *args: Any, **kwargs: Any) -> None:
        self._var = tk.StringVar(master)
        super().__init__(master, *args, textvariable=self._var, **kwargs)

    @property
    def text(self) -> str:
        return self._var.get()

    @text.setter
    def text(self, text: str) -> None:
        self._var.set(text)


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


class App(ttkb.Window):
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
            entry.text = renpyify(transcribe(path))
