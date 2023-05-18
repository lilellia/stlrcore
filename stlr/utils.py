from itertools import count
from pathlib import Path
import re
from typing import Iterator


def frange(start: float, stop: float | None = None, step: float | None = None) -> Iterator[float]:
    """Generalize the built-in range function to allow for float arguments."""
    start = float(start)

    if stop is None:
        # frange(stop, step=...) -> arange(0.0, stop, step)
        start, stop = 0.0, start

    if step is None:
        # frange(..., step=None) -> arange(..., step=1.0)
        step = 1.0

    for n in count():
        current = float(start + n * step)

        if step > 0 and current >= stop:
            break

        if step < 0 and current <= stop:
            break

        yield current


def truncate_path(path: Path, highest_parent: str) -> Path:
    if match := re.search(rf"({highest_parent}.*)", str(path)):
        return Path(match.group(1))

    raise ValueError(f"cannot truncate {path} to {highest_parent}")
