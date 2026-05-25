"""Telachat: a small OpenAI-compatible chat client."""

from __future__ import annotations

__version__ = "0.29.0"


def main(argv: list[str] | None = None) -> int:
    from .cli import main as cli_main

    return cli_main(argv)


__all__ = ["main"]
