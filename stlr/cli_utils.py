from pathlib import Path
import platform
import random
from simple_term_menu import TerminalMenu
from string import ascii_letters
import subprocess
from tempfile import gettempdir
from time import sleep
from typing import Iterable


def select(title: str, options: Iterable[str], **kwargs) -> str:
    """Display a menu with the given options, returning the single selection."""
    options = tuple(options)
    menu = TerminalMenu(options, title=title, **kwargs)
    return options[menu.show()]


def confirm(title: str, **kwargs) -> bool:
    """Display a Yes/No confirmation menu. Return True if "Yes" is selected."""
    option = select(title, ("Yes", "No"), **kwargs)
    return option == "Yes"


def temporary_file() -> Path:
    """Randomly generate an unused name for a temporary file."""
    temp_directory = Path(gettempdir())
    while True:
        name = "".join(random.choices(ascii_letters, k=10))
        if not (p := (temp_directory / name)).exists():
            return p


def get_long_text(initial_text: str = "") -> str:
    """Get a block of text from the user, using a text editor."""
    # Create the file and write the initial text
    path = temporary_file()
    path.write_text(initial_text, encoding="utf-8")

    # Open the file in a text editor
    command = ["notepad" if platform.platform() == "Windows" else "nano", path]
    subprocess.run(command)
    sleep(1)

    user_input = path.read_text(encoding="utf-8")
    path.unlink(missing_ok=True)

    return user_input
