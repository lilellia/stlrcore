from itertools import count
from typing import Iterator


def arange(start: float, stop: float | None = None, step: float | None = None) -> Iterator[float]:
    """Generalize the built-in range function to allow for float arguments."""
    start = float(start)

    if stop is None:
        # arange(stop, step=...) -> arange(0.0, stop, step)
        start, stop = 0.0, start

    if step is None:
        # arange(..., step=None) -> arange(..., step=1.0)
        step = 1.0

    for n in count():
        current = float(start + n * step)

        if step > 0 and current >= stop:
            break

        if step < 0 and current <= stop:
            break

        yield current
