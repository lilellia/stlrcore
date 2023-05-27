from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from tkinter.filedialog import askopenfilenames

from stlr.config import CONFIG
from stlr.transcribe import Transcription


def main():
    parser = ArgumentParser()
    parser.add_argument("-a", "--audio", dest="files", type=Path, nargs="+")
    parser.add_argument("-f", "--format", choices=("json", "tsv"), default=CONFIG.étoile_settings.export_format)
    parser.add_argument("-m", "--model", default=CONFIG.model.name)
    parser.add_argument("--cpu", action="store_const", const="cpu", dest="device", default=None)
    args = parser.parse_args()

    if args.files is None:
        args.files = map(Path, askopenfilenames())

    for file in args.files:
        transcription = Transcription.from_audio(file, model_name=args.model, device=args.device)
        
        transcription.export(Path(f"étoile-{file.stem}-{args.model}-{datetime.now():%Y%m%d-%H%M%S}.{args.format}"), mode=args.format)
        print(transcription.tabulate())


if __name__ == "__main__":
    main()
