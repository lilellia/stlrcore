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
