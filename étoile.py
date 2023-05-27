from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path
from tkinter.filedialog import askopenfilename
import yaml

from stlr.transcribe import Transcription


with open(Path(__file__).parent / "config.yaml") as f:
    config = yaml.safe_load(f)

WHISPER_MODEL = config["transcription_models"]["whisper"]
WHISPER_SETTINGS = config["whisper_settings"]

def main():
    parser = ArgumentParser()
    parser.add_argument("-a", "--audio", dest="file", type=Path)
    parser.add_argument("-m", "--model", default=WHISPER_MODEL)
    args = parser.parse_args()

    if args.file is None:
        args.file = Path(askopenfilename())

    output = Transcription.from_audio(args.file, model_name=args.model).tabulate()
    
    with open(f"étoile-{args.model}-{datetime.now():%Y%m%d-%H%M%S}.txt", "w", encoding="utf-8") as f:
        f.write(output)
    print(output)


if __name__ == "__main__":
    main()
