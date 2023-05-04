from pathlib import Path
import tkinter as tk
from tkinter.filedialog import askopenfilename
import ttkbootstrap as ttkb  # type: ignore
from typing import Any


from stlr.audio import disable_vosk_logging
from stlr.vn import transcribe_with_pauses


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
        disable_vosk_logging()
        super().__init__(*args, **kwargs)  # type: ignore
        self.init_components()

    def init_components(self) -> None:
        # audio file selector
        ttkb.Label(self, text="Audio File").grid(row=1, column=0, padx=20, pady=20)

        self.filename_entry = CEntry(self, width=45)
        self.filename_entry.grid(row=1, column=1, padx=20, pady=20, sticky="nsew")

        self.filename_select = ttkb.Button(self, command=self._load_file, text="Choose File")
        self.filename_select.grid(row=1, column=2, padx=20, pady=20, sticky="nsew")

        # correct transcription
        ttkb.Label(self, text="Correct transcription").grid(row=2, column=0, padx=20, pady=10)

        self.ctranscription_entry = CEntry(self, width=100)
        self.ctranscription_entry.grid(row=2, column=1, columnspan=2, padx=20, pady=10, sticky="nsew")

        # run button
        self.transcribe_btn = ttkb.Button(self, command=self._transcribe, text="Transcribe!")
        self.transcribe_btn.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=20, pady=10)

        # result text
        ttkb.Label(self, text="renpy.say").grid(row=4, column=0, padx=20, pady=20)

        self.renpy_say = CEntry(self, width=100)
        self.renpy_say.grid(row=4, column=1, columnspan=2, padx=20, pady=20, sticky="nsew")

    def _load_file(self) -> None:
        filename = askopenfilename()
        self.filename_entry.text = filename

    def _transcribe(self) -> None:
        filepath = Path(self.filename_entry.get())
        renpy = transcribe_with_pauses(
            correct_transcription=self.ctranscription_entry.get(),
            audio_file=filepath,
            language="en-us"
        )

        self.renpy_say.text = renpy
