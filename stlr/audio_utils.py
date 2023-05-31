from loguru import logger
from pathlib import Path
import pydub
import re
import subprocess
from typing import Iterator
import wave


def convert_to_wav(audio_file: str | Path) -> Path:
    """Convert the given audio file to WAV mono PCM, returning the new path."""
    dest = Path(audio_file).with_suffix(".wav")

    audio = pydub.AudioSegment.from_file(audio_file)
    audio.export(dest, format="wav", parameters=("-ac", "1"))

    logger.success(f"conversion successful: {dest}")
    return dest


def get_volume(audio_file: Path, interval: float) -> Iterator[float]:
    """Determine the average volume over time for the given audio file."""
    # sox <file> -n trim 0 <interval> stats : newfile : restart 2>&1 | grep 'RMS lev dB' | awk '{ print $2 }'
    command = ("sox", str(audio_file), "-n", "trim", "0", str(interval), "stats", ":", "newfile", ":", "restart")
    proc = subprocess.run(command, capture_output=True)
    proc.check_returncode()

    for line in proc.stderr.decode().splitlines():
        if match := re.match(r"^RMS lev dB\s*(.*)", line):
            volume = float(match.group(1).split()[0])
            yield volume


def load_audio(audio_file: str | Path) -> wave.Wave_read:
    """Load the given audio file, converting to WAV mono PCM as necessary."""
    try:
        return load_wav(audio_file)
    except ValueError:
        # not a valid format, so convert
        logger.warning(f"audio file {audio_file} is not WAV mono PCM. Converting...")
        return load_wav(convert_to_wav(audio_file))


def load_wav(audio_file: str | Path) -> wave.Wave_read:
    """Attempt to load the given audio file. If not WAV mono PCM, abort."""
    if Path(audio_file).suffix != ".wav":
        raise ValueError(f"audio file {audio_file} must be WAV format mono PCM")

    audio = wave.open(str(audio_file), "rb")

    if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getcomptype() != "NONE":
        raise ValueError(f"audio file {audio_file} must be WAV format mono PCM")

    return audio
