"""
Local stub of the `colorama` package to avoid ctypes/Windows issues.

This provides just enough surface area for Werkzeug and Flask to run without
depending on the real colorama implementation.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, IO, Optional


def init(*args: Any, **kwargs: Any) -> None:
    """No-op init to satisfy Werkzeug/colorama usage."""
    return None


def deinit(*args: Any, **kwargs: Any) -> None:
    """No-op deinit."""
    return None


def reinit(*args: Any, **kwargs: Any) -> None:
    """No-op reinit."""
    return None


@contextmanager
def colorama_text(*args: Any, **kwargs: Any):
    """Context manager that yields without modification."""
    yield


def just_fix_windows_console(*args: Any, **kwargs: Any) -> None:
    """No-op Windows console fixer."""
    return None


class AnsiToWin32:
    """
    Minimal stub of colorama.ansitowin32.AnsiToWin32.

    Werkzeug uses this to wrap stdout/stderr for colored output.
    This version just forwards write/flush to the underlying stream if provided.
    """

    def __init__(
        self,
        stream: Optional[IO[str]] = None,
        convert: bool | None = None,
        strip: bool | None = None,
        autoreset: bool = False,
    ) -> None:
        self.stream = stream

    def write(self, text: str) -> None:
        if self.stream is not None:
            self.stream.write(text)

    def flush(self) -> None:
        if self.stream is not None:
            self.stream.flush()

