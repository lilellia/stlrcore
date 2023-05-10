from itertools import chain
from pathlib import Path
import tkinter as tk
from tkinter.filedialog import askopenfilenames
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

        self.transcribe_btn = ttkb.Button(self, text="Transcribe", command=self.transcribe, bootstyle="info")
        self.transcribe_btn.grid(row=i+1, column=0, columnspan=3, sticky="nsew", padx=10, pady=10)

    def transcribe(self) -> None:
        for path, entry in zip(self.filenames, self.transcriptions):
            entry.text = renpyify(transcribe(path))
