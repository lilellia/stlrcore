from loguru import logger
from pathlib import Path
import pydub  # type: ignore
import vosk  # type: ignore
import wave


def disable_vosk_logging() -> None:
    vosk.SetLogLevel(-1)  # type: ignore


def convert_to_wav(audio_file: Path) -> Path:
    dest = audio_file.with_suffix(".wav")
    audio = pydub.AudioSegment.from_file(audio_file)  # type: ignore

    audio.export(dest, format="wav", parameters=["-ac", "1"])  # type: ignore
    return dest


def load_wav(wavfile: Path) -> wave.Wave_read:
    if wavfile.suffix != ".wav":
        raise ValueError(f"audio file {wavfile} must be WAV format mono PCM")

    audio = wave.open(str(wavfile), "rb")

    if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getcomptype() != "NONE":
        raise ValueError("audio file must be WAV format mono PCM")

    return audio


def load_audio(audio_file: Path) -> wave.Wave_read:
    try:
        return load_wav(audio_file)
    except ValueError:
        # not a valid format, so convert
        logger.warning(f"{audio_file} is not WAV mono PCM. Converting...")
        converted = convert_to_wav(audio_file)
        return load_wav(converted)


def build_recognizer(audio: wave.Wave_read, language: str = "en-us") -> vosk.KaldiRecognizer:
    model = vosk.Model(lang=language)
    r = vosk.KaldiRecognizer(model, audio.getframerate())
    r.SetMaxAlternatives(10)  # type: ignore
    r.SetWords(True)  # type: ignore

    return r
