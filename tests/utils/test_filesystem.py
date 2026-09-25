from __future__ import annotations

from pathlib import Path

from forgepy.utils.filesystem import LocalFileSystem, MemoryFileSystem


def test_memory_filesystem_write_read_roundtrip():
    fs = MemoryFileSystem()
    fs.write_text(Path("a/b.txt"), "hello")
    assert fs.exists(Path("a/b.txt"))
    assert fs.read_text(Path("a/b.txt")) == "hello"


def test_memory_filesystem_unlink_removes_file():
    fs = MemoryFileSystem()
    fs.write_text(Path("a.txt"), "hello")
    fs.unlink(Path("a.txt"))
    assert not fs.exists(Path("a.txt"))


def test_local_filesystem_write_read_roundtrip(tmp_path: Path):
    fs = LocalFileSystem()
    target = tmp_path / "a.txt"
    fs.write_text(target, "hello")
    assert fs.exists(target)
    assert fs.read_text(target) == "hello"
    fs.unlink(target)
    assert not fs.exists(target)


def test_local_filesystem_mkdir_creates_parents(tmp_path: Path):
    fs = LocalFileSystem()
    nested = tmp_path / "a" / "b"
    fs.mkdir(nested, parents=True)
    assert nested.is_dir()
