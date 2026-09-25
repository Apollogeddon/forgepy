from __future__ import annotations

from importlib import resources


def load_config(name: str) -> str:
    """Read a base config shipped in forgepy.configs (package data)."""
    return resources.files("forgepy.configs").joinpath(name).read_text(encoding="utf-8")
