from __future__ import annotations

from pathlib import Path

import pytest

from forgepy.utils.filesystem import MemoryFileSystem


@pytest.fixture
def memfs() -> MemoryFileSystem:
    return MemoryFileSystem()


@pytest.fixture
def project_dir() -> Path:
    return Path("project")
