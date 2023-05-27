from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from tkinter.filedialog import askopenfilenames

from stlr.config import CONFIG
from stlr.transcribe import Transcription


def main():
    parser = ArgumentParser()
    parser.add_argument("-a", "--audio", dest="files", type=Path, nargs="+")
    parser.add_argument("-m", "--model", default=CONFIG.transcription_models.whisper)
    args = parser.parse_args()

    if args.files is None:
        args.files = map(Path, askopenfilenames())

    for file in args.files:
        transcription = Transcription.from_audio(file, model_name=args.model)

        transcription.export(Path(f"étoile-{file.stem}-{args.model}-{datetime.now():%Y%m%d-%H%M%S}.json"))
        print(transcription.tabulate())


if __name__ == "__main__":
    main()
