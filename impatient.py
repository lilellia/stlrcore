from pathlib import Path
import re
import shutil
from tkinter.filedialog import askopenfilenames


def remove_waits(file: Path):
    out = re.sub(r"\{w=.+?\}", "", file.read_text())
    file.write_text(out)


def main():
    files = map(Path, askopenfilenames())
    for file in files:
        shutil.copy(file, file.with_suffix(".bak"))
        remove_waits(file)


if __name__ == "__main__":
    main()
