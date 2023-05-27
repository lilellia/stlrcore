from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from tkinter.filedialog import askopenfilename

from stlr.transcribe import Transcription


def main():
    parser = ArgumentParser()
    parser.add_argument("-a", "--audio", dest="file", type=Path, default=None)
    args = parser.parse_args()

    if args.file is None:
        args.file = Path(askopenfilename())

    output = Transcription.from_audio(args.file).tabulate()
    
    with open(f"étoile-{datetime.now():%Y%m%d-%H%M%S}.txt", "w", encoding="utf-8") as f:
        f.write(output)
    print(output)


if __name__ == "__main__":
    main()
