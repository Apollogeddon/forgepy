from __future__ import annotations

from pathlib import Path

from forgepy import templates
from forgepy.sync import sync
from forgepy.utils.filesystem import MemoryFileSystem

PROJECT = Path("project")


def test_sync_writes_missing_managed_configs():
    fs = MemoryFileSystem()
    assert sync(PROJECT, fs=fs) == 0
    assert fs.read_text(PROJECT / ".forgepy/ruff.toml") == templates.load_config("ruff.toml")
    assert fs.read_text(PROJECT / ".forgepy/pyrightconfig.json") == templates.load_config("pyrightconfig.json")


def test_sync_refreshes_stale_managed_configs():
    fs = MemoryFileSystem()
    fs.write_text(PROJECT / ".forgepy/ruff.toml", "stale content")
    assert sync(PROJECT, fs=fs) == 0
    assert fs.read_text(PROJECT / ".forgepy/ruff.toml") == templates.load_config("ruff.toml")


def test_sync_is_noop_when_already_current():
    fs = MemoryFileSystem()
    sync(PROJECT, fs=fs)
    assert sync(PROJECT, fs=fs) == 0
    assert fs.read_text(PROJECT / ".forgepy/ruff.toml") == templates.load_config("ruff.toml")


def test_sync_check_returns_zero_when_up_to_date():
    fs = MemoryFileSystem()
    sync(PROJECT, fs=fs)
    assert sync(PROJECT, check=True, fs=fs) == 0


def test_sync_check_returns_nonzero_when_missing():
    fs = MemoryFileSystem()
    assert sync(PROJECT, check=True, fs=fs) == 1


def test_sync_check_returns_nonzero_when_stale():
    fs = MemoryFileSystem()
    sync(PROJECT, fs=fs)
    fs.write_text(PROJECT / ".forgepy/ruff.toml", "tampered")
    assert sync(PROJECT, check=True, fs=fs) == 1


def test_sync_check_does_not_write():
    fs = MemoryFileSystem()
    assert sync(PROJECT, check=True, fs=fs) == 1
    assert not fs.exists(PROJECT / ".forgepy/ruff.toml")
