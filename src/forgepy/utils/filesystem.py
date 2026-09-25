from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileSystem(Protocol):
    def cwd(self) -> Path: ...
    def exists(self, path: Path) -> bool: ...
    def mkdir(self, path: Path, *, parents: bool = True) -> None: ...
    def read_text(self, path: Path) -> str: ...
    def write_text(self, path: Path, content: str) -> None: ...
    def unlink(self, path: Path) -> None: ...


class LocalFileSystem:
    def cwd(self) -> Path:
        return Path.cwd()

    def exists(self, path: Path) -> bool:
        return path.exists()

    def mkdir(self, path: Path, *, parents: bool = True) -> None:
        path.mkdir(parents=parents, exist_ok=True)

    def read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def write_text(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8", newline="\n")

    def unlink(self, path: Path) -> None:
        path.unlink()


class MemoryFileSystem:
    """In-memory filesystem for fast, deterministic feature/core tests."""

    def __init__(self, initial_files: dict[str, str] | None = None) -> None:
        self._files: dict[str, str] = dict(initial_files or {})
        self._dirs: set[str] = set()

    @staticmethod
    def _key(path: Path) -> str:
        return path.as_posix()

    def cwd(self) -> Path:
        return Path(".")

    def exists(self, path: Path) -> bool:
        key = self._key(path)
        return key in self._files or key in self._dirs

    def mkdir(self, path: Path, *, parents: bool = True) -> None:
        self._dirs.add(self._key(path))

    def read_text(self, path: Path) -> str:
        try:
            return self._files[self._key(path)]
        except KeyError:
            raise FileNotFoundError(path) from None

    def write_text(self, path: Path, content: str) -> None:
        self._files[self._key(path)] = content

    def unlink(self, path: Path) -> None:
        key = self._key(path)
        if key not in self._files:
            raise FileNotFoundError(path)
        del self._files[key]

    def read(self, rel_path: str) -> str | None:
        return self._files.get(rel_path)
