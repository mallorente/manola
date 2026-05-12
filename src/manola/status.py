from __future__ import annotations

from collections.abc import Callable


StatusCallback = Callable[[str], None]


def noop_status(message: str) -> None:
    return None
