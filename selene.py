from loguru import logger
from pathlib import Path
import sys
import tkinter.font
from tkinter.filedialog import askopenfilename

from stlr.audio_utils import audio_only, is_audio_only
from stlr.cli_utils import confirm, get_long_text
from stlr.transcribe import Segment, Transcription, WordTiming


def get_system_fonts() -> list[str]:
    """Return a list of all fonts on the system."""
    return sorted(tkinter.font.families())


def get_audio_file() -> Path:
    """Get the path to the desired audio file."""
    media_file = Path(askopenfilename())

    if not confirm(title=f"Use: {media_file}?", clear_menu_on_exit=False):
        logger.info("Exiting...")
        sys.exit(1)

    if is_audio_only(media_file):
        audio_file = media_file
    else:
        print(f"extracting audio from {media_file}...")
        audio_file = audio_only(media_file)
        print("✓ audio extracted")

    return audio_file


def main():
    print("Σελήνη (Selene)")
    print("===============")

    # Get the audio file and generate a transcription for it.
    input("\nStep 1: Select the media file you wish to analyse. (Press ENTER to continue.)")
    try:
        audio_file = get_audio_file()
    except ValueError:
        sys.exit(f"Error: selected file is not a media file and cannot be used.")

    print("Generating transcription...")
    transcription = Transcription.from_audio(audio_file)

    # Have the user insert breaks for the different fragments.
    message = """
Step 2: Separate the transcription into individual lines. These lines will be the different "screens" of text.
This step will open a text editor. Make your changes, save the file, then close the editor.
(On MacOS/Linux, this opens nano. Use Ctrl+O to save (enter to confirm), then Ctrl+X to close.) 

-NOTE:- Do __not__ edit or correct any of the text. Just separate it into lines.

(Press ENTER to continue.)
"""
    input(message)

    segments = get_long_text(initial_text=str(transcription)).splitlines()
    segments = [transcription.get_fragment(line.strip()) for line in segments]

    # We're going to abuse WordTiming and give it multiple words for this purpose.
    # It's really a "BlockTiming" or "SegmentTiming" like this.
    segments = [WordTiming(word=str(s), start=s.start, end=s.end) for s in segments]

    # Correct spellings, etc.
    message = """
Step 3: Now that the "screen" timings are set, fix or edit any transcription errors, including corrections to spelling or punctuation.
As before, this will open a text editor.

(Press ENTER to continue.)
"""
    input(message)

    initial_text = "\n".join(segment.word for segment in segments)
    new_segments = get_long_text(initial_text)

    segments = [
        # update the text
        WordTiming(word=line.strip(), start=s.start, end=s.end)
        for line, s in zip(new_segments.splitlines(), segments)
    ]

    # Convert to "actual" segment objects
    segments = [Segment([s], wait_after=0.0) for s in segments]

    # Output .srt
    dest = audio_file.with_suffix(".srt")
    Transcription.write_srt(segments, dest=dest)

    if confirm(f"Subtitles written to {dest}. Show them?"):
        print(dest.read_text())


if __name__ == "__main__":
    main()
