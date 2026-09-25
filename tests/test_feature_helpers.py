from __future__ import annotations

from pathlib import Path

import tomlkit

from forgepy.config import InitConfig
from forgepy.features.feature import (
    FeatureContext,
    create_file,
    remove_file,
    write_managed,
)
from forgepy.utils.filesystem import MemoryFileSystem


def _ctx(fs: MemoryFileSystem, project_dir: Path, **overrides) -> FeatureContext:
    cfg = InitConfig(target=project_dir, **overrides)
    return FeatureContext(cwd=project_dir, cfg=cfg, fs=fs, pyproject=tomlkit.document())


def test_create_file_writes_when_missing(memfs: MemoryFileSystem, project_dir: Path):
    ctx = _ctx(memfs, project_dir)
    assert create_file(ctx, "a.txt", "hello") is True
    assert memfs.read_text(project_dir / "a.txt") == "hello"


def test_create_file_skips_existing_without_force(
    memfs: MemoryFileSystem, project_dir: Path
):
    ctx = _ctx(memfs, project_dir)
    create_file(ctx, "a.txt", "hello")
    assert create_file(ctx, "a.txt", "changed") is True
    assert memfs.read_text(project_dir / "a.txt") == "hello"


def test_create_file_overwrites_with_force(memfs: MemoryFileSystem, project_dir: Path):
    ctx = _ctx(memfs, project_dir)
    create_file(ctx, "a.txt", "hello")
    ctx_force = _ctx(memfs, project_dir, force=True)
    assert create_file(ctx_force, "a.txt", "changed") is True
    assert memfs.read_text(project_dir / "a.txt") == "changed"


def test_create_file_dry_run_does_not_write(memfs: MemoryFileSystem, project_dir: Path):
    ctx = _ctx(memfs, project_dir, dry_run=True)
    assert create_file(ctx, "a.txt", "hello") is True
    assert not memfs.exists(project_dir / "a.txt")


def test_create_file_dry_run_does_not_create_directory(
    memfs: MemoryFileSystem, project_dir: Path
):
    ctx = _ctx(memfs, project_dir, dry_run=True)
    create_file(ctx, "nested/a.txt", "hello")
    assert not memfs.exists(project_dir / "nested")


def test_write_managed_ignores_force_flag_but_always_refreshes(
    memfs: MemoryFileSystem, project_dir: Path
):
    ctx = _ctx(memfs, project_dir)
    write_managed(ctx, ".forgepy/ruff.toml", "v1")
    write_managed(ctx, ".forgepy/ruff.toml", "v2")
    assert memfs.read_text(project_dir / ".forgepy/ruff.toml") == "v2"


def test_write_managed_dry_run_does_not_write(
    memfs: MemoryFileSystem, project_dir: Path
):
    ctx = _ctx(memfs, project_dir, dry_run=True)
    write_managed(ctx, ".forgepy/ruff.toml", "v1")
    assert not memfs.exists(project_dir / ".forgepy/ruff.toml")


def test_remove_file_noop_when_missing(memfs: MemoryFileSystem, project_dir: Path):
    ctx = _ctx(memfs, project_dir, force=True)
    remove_file(ctx, "missing.txt")  # should not raise


def test_remove_file_requires_force(memfs: MemoryFileSystem, project_dir: Path):
    ctx = _ctx(memfs, project_dir)
    create_file(ctx, "a.txt", "hello")
    remove_file(ctx, "a.txt")
    assert memfs.exists(project_dir / "a.txt")


def test_remove_file_deletes_with_force(memfs: MemoryFileSystem, project_dir: Path):
    ctx = _ctx(memfs, project_dir, force=True)
    create_file(ctx, "a.txt", "hello")
    remove_file(ctx, "a.txt")
    assert not memfs.exists(project_dir / "a.txt")


def test_remove_file_dry_run_does_not_delete(
    memfs: MemoryFileSystem, project_dir: Path
):
    create_ctx = _ctx(memfs, project_dir, force=True)
    create_file(create_ctx, "a.txt", "hello")
    dry_ctx = _ctx(memfs, project_dir, force=True, dry_run=True)
    remove_file(dry_ctx, "a.txt")
    assert memfs.exists(project_dir / "a.txt")
