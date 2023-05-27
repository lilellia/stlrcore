from argparse import ArgumentParser
from pathlib import Path
from tkinter.filedialog import askopenfilename

from stlr.transcribe import Transcription


def main():
    parser = ArgumentParser()
    parser.add_argument("-a", "--audio", dest="file", type=Path, default=None)
    args = parser.parse_args()

    if args.file is None:
        args.file = Path(askopenfilename())

    transcription = Transcription.from_audio(args.file)
    print(transcription.tabulate())


if __name__ == "__main__":
    main()
