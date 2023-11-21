from loguru import logger
import os
from pathlib import Path
import tkinter.font
import ttkbootstrap as ttkb

from stlr.audio_utils import audio_only, is_audio_only
from stlr.transcribe import Segment, Transcription, WordTiming
from stlr.ui import CText, CToplevel, file_selection_row
from stlr.utils import CTextLogHandler, open_file


def get_system_fonts() -> list[str]:
    """Return a list of all fonts on the system."""
    return sorted(tkinter.font.families())


GRID_KW = dict(sticky="nsew", padx=10, pady=10)


class Selene(ttkb.Window):
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)

        self.media_file_box, self.media_file_button = file_selection_row(self, row=0, label_text="Media File", grid_kw=GRID_KW)

        button = ttkb.Button(self, text="Transcribe", command=lambda: run(media_file=Path(self.media_file_box.text)))
        button.grid(row=1, column=0, columnspan=3, **GRID_KW)

        # add log container
        log_box = CText(self)
        log_box.configure(state="disabled", font="TkFixedFont")
        log_box.grid(row=10, column=0, columnspan=3, **GRID_KW)

        handler = CTextLogHandler(sink=log_box)
        fmt = '<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>'
        logger.add(handler, format=fmt)


def run(media_file: Path) -> None:
    # Step 0: Load file
    try:
        a = is_audio_only(media_file)
    except ValueError:
        logger.error(f"{media_file} is not a valid media file.")
        return

    if a:
        audio_file = media_file
        logger.debug(f"{audio_file} is already an audio file")
    else:
        logger.info(f"{media_file} is not an audio file. Converting...")
        audio_file = audio_only(media_file)
        logger.success(f"Conversion successful: {audio_file}")

    # Step 1: Generate transcription
    logger.info("Generating transcription...")
    transcription = Transcription.from_audio(audio_file)
    logger.success("Transcription generated.")

    # Step 2: Get segments
    segments: list[WordTiming] = user_split_transcription(transcription)
    logger.success("Segments confirmed.")

    # Step 3: Correct transcriptions
    segments: list[Segment] = user_correct_transcription(segments)
    logger.success("Corrections confirmed.")

    # Step 4: Output to SRT
    dest = media_file.with_suffix(".srt")
    Transcription.write_srt(segments, dest=dest)
    logger.success(f"SRT file written: {dest}")
    open_file(dest)


def user_split_transcription(transcription: Transcription) -> list[WordTiming]:
    """Have the user split the given transcription into individual segments."""
    window: CToplevel[list[WordTiming]] = CToplevel(title="Σελήνη: Split Transcription")

    message = "Separate the transcription into individual segments.\nDo NOT edit or correct the transcription."
    ttkb.Label(window, text=message) \
        .grid(row=0, column=0, **GRID_KW)

    textbox = CText(window)
    textbox.text = str(transcription)
    textbox.grid(row=1, column=0, **GRID_KW)

    def process_splits():
        fragments = (line.strip() for line in textbox.text.splitlines())
        segments = (transcription.get_fragment(f) for f in fragments)

        # conflate each segment (a list of word timings) into one WordTiming, which is a bit of an abuse
        # of the class, but at this point, we no longer care about the timing of the individual words, just
        # the segment as a whole
        word_timings = [WordTiming(word=str(s), start=s.start, end=s.end) for s in segments]
        window.return_(word_timings)

    ttkb.Button(window, text="Confirm Segments", command=process_splits) \
        .grid(row=2, column=0, **GRID_KW)

    return window.result() or []


def user_correct_transcription(segments: list[WordTiming]) -> list[Segment]:
    """Have the user correct errors, punctuation, etc. in the transcriptions."""
    window: CToplevel[list[WordTiming]] = CToplevel(title="Σελήνη: Correct Transcription")

    message = "Make any edits to the transcription, including spelling or punctuation.\nDo NOT edit any line breaks."
    ttkb.Label(window, text=message) \
        .grid(row=0, column=0, **GRID_KW)

    textbox = CText(window)
    textbox.text = "\n".join(segment.word for segment in segments)
    textbox.grid(row=1, column=0, **GRID_KW)

    def process_splits():
        corrected_segments: list[Segment] = []

        lines = (line.strip() for line in textbox.text.splitlines())
        for line, segment in zip(lines, segments):
            segment.word = line
            corrected_segments.append(Segment(words=[segment], wait_after=0.0))

        window.return_(corrected_segments)

    ttkb.Button(window, text="Confirm Segments", command=process_splits) \
        .grid(row=2, column=0, **GRID_KW)

    return window.result() or []

#     # Correct spellings, etc.
#     message = """
# Step 3: Now that the "screen" timings are set, fix or edit any transcription errors, including corrections to spelling or punctuation.
# As before, this will open a text editor.
#
# (Press ENTER to continue.)
# """
#     input(message)
#
#     initial_text = "\n".join(segment.word for segment in segments)
#     new_segments = get_long_text(initial_text)
#
#     segments = [
#         # update the text
#         WordTiming(word=line.strip(), start=s.start, end=s.end)
#         for line, s in zip(new_segments.splitlines(), segments)
#     ]
#
#     # Convert to "actual" segment objects
#     segments = [Segment([s], wait_after=0.0) for s in segments]
#
#     # Output .srt
#     dest = audio_file.with_suffix(".srt")
#     Transcription.write_srt(segments, dest=dest)
#
#     if confirm(f"Subtitles written to {dest}. Show them?"):
#         print(dest.read_text())


if __name__ == "__main__":
    Selene(title="Σελήνη (Selene)", themename="darkly").mainloop()
