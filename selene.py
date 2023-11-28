from attrs import define
from loguru import logger
from pathlib import Path
import tkinter.font
import ttkbootstrap as ttkb

from stlr.audio_utils import audio_only, is_audio_only
from stlr.transcribe import Segment, Transcription, WordTiming
from stlr.ui import CCombobox, CEntry, CText, CToplevel, file_selection_row
from stlr.utils import CTextLogHandler


def get_system_fonts() -> list[str]:
    """Return a list of all fonts on the system."""
    return sorted(tkinter.font.families())


GRID_KW = dict(sticky="nsew", padx=10, pady=10)


@define
class SubtitleConfig:
    bounding_box: tuple[int, int, int, int]
    font: str
    fontsize: int
    start_time: float
    end_time: float


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
    word_timings = user_split_transcription(transcription)
    logger.success("Segments confirmed.")

    # Step 3: Correct transcriptions
    segments = user_correct_transcription(word_timings)
    logger.success("Corrections confirmed.")

    # Step 4: Output to SRT
    dest = media_file.with_suffix(".srt")
    Transcription.write_srt(segments, dest=dest)
    logger.success(f"SRT file written: {dest}")

    # Step 5: Get subtitle configuration
    while (config := get_subtitle_config()) is None:
        logger.error("Configuration not processed. Try again.")

    # Step 6: Start building

    print(config)


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
    window: CToplevel[list[Segment]] = CToplevel(title="Σελήνη: Correct Transcription")

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


def get_subtitle_config() -> SubtitleConfig | None:
    window: CToplevel[SubtitleConfig] = CToplevel(title="Σελήνη: Subtitle Configuration")

    # Subtitle bounding box
    ttkb.Label(window, text="Subtitle bounding box") \
        .grid(row=1, column=0, **GRID_KW)

    bbox_x_entry = CEntry(window, text="(x)", converter=int, validator=(0).__lt__)
    bbox_x_entry.grid(row=1, column=1, **GRID_KW)

    bbox_y_entry = CEntry(window, text="(y)", converter=int, validator=(0).__lt__)
    bbox_y_entry.grid(row=1, column=2, **GRID_KW)

    bbox_w_entry = CEntry(window, text="(width)", converter=int, validator=(0).__lt__)
    bbox_w_entry.grid(row=1, column=3, **GRID_KW)

    bbox_h_entry = CEntry(window, text="(height)", converter=int, validator=(0).__lt__)
    bbox_h_entry.grid(row=1, column=4, **GRID_KW)

    # Font selector
    ttkb.Label(window, text="Subtitle font") \
        .grid(row=2, column=0, **GRID_KW)

    font_selector = CCombobox(window, options=get_system_fonts())
    font_selector.grid(row=2, column=1, columnspan=2, **GRID_KW)

    # Font size
    ttkb.Label(window, text="Font size (pt)") \
        .grid(row=2, column=3, **GRID_KW)

    fontsize_entry = CEntry(window, converter=int, validator=(0).__lt__)
    fontsize_entry.grid(row=2, column=4, **GRID_KW)

    # Start and end times
    ttkb.Label(window, text="Start time (seconds)") \
        .grid(row=3, column=0, **GRID_KW)

    start_time_entry = CEntry(window, text="0.0", converter=float, validator=(0.0).__lt__)
    start_time_entry.grid(row=3, column=1, **GRID_KW)

    ttkb.Label(window, text="End time (seconds)") \
        .grid(row=3, column=2, **GRID_KW)

    end_time_entry = CEntry(window, text="inf", converter=float, validator=(0.0).__lt__)
    end_time_entry.grid(row=3, column=3, **GRID_KW)

    def interpret():
        bounding_box = (bbox_x_entry.value, bbox_y_entry.value, bbox_w_entry.value, bbox_h_entry.value)
        font = font_selector.value
        fontsize = fontsize_entry.value

        start_time = start_time_entry.value
        end_time = end_time_entry.value

        config = SubtitleConfig(
            bounding_box=bounding_box,
            font=font,
            fontsize=fontsize,
            start_time=start_time,
            end_time=end_time
        )
        print(config)
        window.return_(config)

    ttkb.Button(window, text="Generate", command=interpret) \
        .grid(row=100, column=0, columnspan=5, **GRID_KW)

    return window.result()


if __name__ == "__main__":
    Selene(title="Σελήνη (Selene)", themename="darkly").mainloop()
