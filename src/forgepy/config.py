from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

# The Python version a new project pins in .python-version, and the workflows' fallback when a
# project has none. Raise it here; a test keeps the workflows' fallback in step.
DEFAULT_PYTHON_VERSION = "3.13"


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
    # the code runs on Jython 2.7: uv installs only the dev tools, and the checks keep it Python 2 compatible
    jython: bool = False
    python_version: str = DEFAULT_PYTHON_VERSION
    target: Path = field(default_factory=Path.cwd)

    @property
    def packaged(self) -> bool:
        """Whether uv builds and installs the project itself, which needs a module under src/."""
        return not (self.mode.is_website or self.jython)

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.docker and self.mode.is_library:
            errors.append("--docker is not available in library mode")
        if self.debian and not self.mode.is_backend:
            errors.append("--debian is only available in backend mode")
        if self.jython and not self.mode.is_backend:
            errors.append("--jython is only available in backend mode")
        if self.jython and not self.linting:
            errors.append("--jython needs linting: its Python 2 checks are part of it")
        if self.jython and (self.docker or self.debian):
            errors.append("--jython can't be combined with --docker or --debian")
        return errors
