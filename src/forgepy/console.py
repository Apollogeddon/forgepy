from __future__ import annotations

import sys


def setup_stdio() -> None:
    """Windows terminals piped through cp1252 can't encode emoji; replace instead of raising."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")


def ok(message: str) -> None:
    print(f"✅ {message}")


def warn(message: str) -> None:
    print(f"⚠️  {message}")


def err(message: str) -> None:
    print(f"❌ {message}", file=sys.stderr)


def dry(message: str) -> None:
    print(f"[DryRun] {message}")


def info(message: str) -> None:
    print(message)
