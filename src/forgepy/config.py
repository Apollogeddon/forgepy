from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

# The Python version a new project pins in .python-version, and the workflows' fallback when a
# project has none. Raise it here; a test keeps the workflows' fallback in step.
DEFAULT_PYTHON_VERSION = "3.13"
# The image debian.yml's build stage builds in, and the python3 it ships: a --debian project must
# target that Python or older. A test keeps the image in step with the workflow.
DEBIAN_IMAGE = "debian:trixie-slim"
DEBIAN_PYTHON_VERSION = "3.13"
# The oldest Python a project can target: the oldest the tools' configs and images support
MIN_PYTHON_MINOR = 10

_PYTHON_VERSION = re.compile(r"3\.(\d+)(?:\.\d+)?")


def valid_python_version(version: str) -> bool:
    """A CPython 3 release from 3.10 up, as 3.13 or 3.13.1."""
    match = _PYTHON_VERSION.fullmatch(version)
    return match is not None and int(match.group(1)) >= MIN_PYTHON_MINOR


def _minor(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split(".")[:2])


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
    # None takes the project's own pin (core resolves it), else DEFAULT_PYTHON_VERSION
    python_version: str | None = None
    target: Path = field(default_factory=Path.cwd)

    @property
    def packaged(self) -> bool:
        """Whether uv builds and installs the project itself, which needs a module under src/."""
        return not (self.mode.is_website or self.jython)

    @property
    def python(self) -> str:
        """The Python version the project targets."""
        return DEFAULT_PYTHON_VERSION if self.python_version is None else self.python_version

    @property
    def python_minor(self) -> str:
        """The major.minor of the target version, which ruff's target version names."""
        return ".".join(self.python.split(".")[:2])

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not valid_python_version(self.python):
            errors.append(
                f"--python takes a Python version from 3.{MIN_PYTHON_MINOR} up, such as 3.13 or 3.13.1, "
                f"not {self.python!r}"
            )
        elif self.debian and _minor(self.python) > _minor(DEBIAN_PYTHON_VERSION):
            errors.append(
                f"--debian builds on {DEBIAN_IMAGE}, whose python3 is {DEBIAN_PYTHON_VERSION}: "
                f"target Python {DEBIAN_PYTHON_VERSION} or older, not {self.python}"
            )
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
