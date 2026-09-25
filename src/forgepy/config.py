from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class Mode(StrEnum):
    BACKEND = "backend"
    LIBRARY = "library"
    WEBSITE = "website"

    @property
    def is_backend(self) -> bool:
        return self is Mode.BACKEND

    @property
    def is_library(self) -> bool:
        return self is Mode.LIBRARY

    @property
    def is_website(self) -> bool:
        return self is Mode.WEBSITE


@dataclass(frozen=True)
class InitConfig:
    mode: Mode = Mode.BACKEND
    force: bool = False
    dry_run: bool = False
    testing: bool = True
    linting: bool = True
    versioning: bool = True
    docker: bool = False
    debian: bool = False
    python_version: str = "3.13"
    target: Path = field(default_factory=Path.cwd)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.docker and self.mode.is_library:
            errors.append("--docker is not available in library mode")
        if self.debian and not self.mode.is_backend:
            errors.append("--debian is only available in backend mode")
        return errors
