from itertools import islice
import re
from stable_whisper import WhisperResult
from stable_whisper.result import WordTiming
import ttkbootstrap as ttkb
from ttkbootstrap.scrolled import ScrolledFrame
from typing import Any, Callable, Iterator, Literal

from stlr.config import CONFIG
from stlr.ui import CEntry, CToplevel
from stlr.utils import diff_block_str


class HoshiAssistant(CToplevel):
    WHISPER_STYLE = "primary"
    VOSK_STYLE = "danger"
    MATCHING_STYLE = "success"

    def __init__(self, whisper_result: dict[str, Any], vosk_result: list[WordTiming], *args: Any, **kwargs: Any):
        super().__init__("星 hoshi", *args, **kwargs)
        self.whisper_result = whisper_result
        self.vosk_result = vosk_result

        self.init_components(whisper_text=whisper_result["text"], vosk_text=" ".join(v.word for v in vosk_result))

    def init_components(self, whisper_text: str, vosk_text: str) -> None:
        grid_kw = dict(sticky="nsew", padx=10, pady=10)

        sf = ScrolledFrame(self)
        frame = sf.container

        ttkb.Button(frame, text="whisper", bootstyle=self.WHISPER_STYLE).grid(row=0, column=0, **grid_kw)
        ttkb.Button(frame, text="vosk", bootstyle=self.VOSK_STYLE).grid(row=0, column=1, **grid_kw)

        self.word_parts: dict[Literal["whisper", "vosk", "matching"], list[CEntry]] = {"whisper": [], "vosk": [], "matching": []}

        for i, (whisper_only, vosk_only, matching) in enumerate(diff_block_str(whisper_text, vosk_text), start=1):
            w = CEntry(frame, text=whisper_only, width=60, bootstyle=self.WHISPER_STYLE)
            w.grid(row=2*i, column=0, **grid_kw)
            self.word_parts["whisper"].append(w)

            v = CEntry(frame, text=vosk_only, width=60, bootstyle=self.VOSK_STYLE)
            v.grid(row=2*i, column=1, **grid_kw)
            self.word_parts["vosk"].append(v)

            m = CEntry(frame, text=matching, width=80, bootstyle=self.MATCHING_STYLE)
            m.grid(row=2*i+1, column=0, columnspan=2, **grid_kw)
            self.word_parts["matching"].append(m)

        self.update_button = ttkb.Button(frame, text="Update", bootstyle="primary", command=self.update)
        self.update_button.grid(row=2*i+2, column=0, columnspan=3, **grid_kw)

        sf.pack(fill="both", expand=True)

    def _iter_rows(self) -> Iterator[tuple[str, str, str]]:
        """Iterate over the "rows" of the UI: (whisper, vosk, matching)"""
        for whisper_entry, vosk_entry, matching_entry in zip(self.word_parts["whisper"], self.word_parts["vosk"], self.word_parts["matching"]):
            yield whisper_entry.text, vosk_entry.text, matching_entry.text

    def reconcile(self) -> Iterator[WordTiming]:
        """Intercede to combine the whisper transcription with the vosk timings, appropriately grouped."""
        true_transcription = iter(self.whisper_result["text"].split())
        timings = iter(self.vosk_result)

        def _reconcile_one(whisper_phrase: str, vosk_phrase: str) -> Iterator[WordTiming]:
            """Reconcile a single disagreed segment."""
            # form the segments by splitting on the slashes
            whisper_segments = re.split(r"\s*/\s*", whisper_phrase)
            vosk_segments = re.split(r"\s*/\s*", vosk_phrase)

            for whisper_segment, vosk_segment in zip(whisper_segments, vosk_segments):
                n_whisper = len(whisper_segment.split())
                text = ' '.join(islice(true_transcription, n_whisper))

                if not (n_vosk := len(vosk_segment.split())):
                    # number of word timings to strip out for this segment
                    continue

                vosk_words = tuple(islice(timings, n_vosk))
                yield WordTiming(word=text, start=vosk_words[0].start, end=vosk_words[-1].end)

        def _reconcile_matching(matching_phrase: str) -> Iterator[WordTiming]:
            """Reconcile a single matching sequence."""
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

        # Assign result so that it can be accessed externally via .result()
        self._result = WhisperResult(self.whisper_result)
        self.destroy()


def _reconcile_equal_simple(whisper_result: dict[str, Any], vosk_result: list[WordTiming]) -> WhisperResult:
    """Construct a WhisperResult by combining the timing results from vosk with the untimed transcriptions from whisper."""
    vosk_words = iter(vosk_result)

    for segment in whisper_result["segments"]:
        whisper_words = segment["text"].split()
        segment["words"] = [v for v, _ in zip(vosk_words, whisper_words)]

    return WhisperResult(whisper_result)

def _reconcile_unequal_simple(whisper_result: dict[str, Any], vosk_result: list[WordTiming]) -> WhisperResult:
    """Reconcile by just... ignoring whisper's transcription entirely."""

    # create a single transcription segment from vosk's data,
    # then use it to overwrite the original segments data
    segment = {
        "start": min(w.start for w in vosk_result),
        "end": max(w.end for w in vosk_result),
        "words": vosk_result,
        "text": " ".join(w.word for w in vosk_result)
    }

    whisper_result["segments"] = [segment]
    return WhisperResult(whisper_result)


def _reconcile_assisted(whisper_result: dict[str, Any], vosk_result: list[WordTiming]) -> WhisperResult:
    """Reconcile by allowing the hoshi assistant to intercede."""
    assistant = HoshiAssistant(whisper_result, vosk_result)
    return assistant.result()


def reconcile(whisper_result: dict[str, Any], vosk_result: list[WordTiming], *, mode: str = "assisted") -> WhisperResult:
    nwords_whisper = len(whisper_result["text"].split())
    nwords_vosk = len(vosk_result)

    if nwords_whisper == nwords_vosk and mode != "always-assisted":
        # This is the easy case, where the two transcriptions have the
        # same number of words
        return _reconcile_equal_simple(whisper_result, vosk_result)

    # The more difficult case, where we need to figure out how to group
    # together the words in the different transcriptions and line them up.

    if mode == "simple":
        # just...avoid the difficulty ^_^
        return _reconcile_unequal_simple(whisper_result, vosk_result)

    # Okay, fine... we'll engage.
    return _reconcile_assisted(whisper_result, vosk_result)
