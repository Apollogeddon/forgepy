from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from tomlkit import TOMLDocument

from forgepy import console
from forgepy.config import InitConfig
from forgepy.utils.filesystem import FileSystem


@dataclass
class FeatureContext:
    cwd: Path
    cfg: InitConfig
    fs: FileSystem
    pyproject: TOMLDocument


class Feature(ABC):
    name: ClassVar[str]

    @abstractmethod
    def should_run(self, cfg: InitConfig) -> bool: ...

    @abstractmethod
    def apply(self, ctx: FeatureContext) -> bool: ...

    def cleanup(self, ctx: FeatureContext) -> None:  # noqa: ARG002 - default no-op override point
        return None


def create_file(ctx: FeatureContext, rel_path: str, content: str) -> bool:
    path = ctx.cwd / rel_path
    try:
        exists = ctx.fs.exists(path)
        if exists and not ctx.cfg.force:
            console.info(f"{rel_path} already exists. Skipping.")
            return True

        if ctx.cfg.dry_run:
            verb = "overwrite" if exists else "create"
            console.dry(f"Would {verb} {rel_path}")
            return True

        parent = path.parent
        if not ctx.fs.exists(parent):
            ctx.fs.mkdir(parent, parents=True)
        ctx.fs.write_text(path, content)
        console.ok(f"{'Overwrote' if exists else 'Created'} {rel_path}")
        return True
    except OSError as exc:
        console.err(f"Failed to write {rel_path}: {exc}")
        return False


def write_managed(ctx: FeatureContext, rel_path: str, content: str) -> bool:
    """Forgepy-owned files under .forgepy/ always refresh, ignoring --force."""
    path = ctx.cwd / rel_path
    try:
        if ctx.cfg.dry_run:
            console.dry(f"Would refresh managed file {rel_path}")
            return True

        parent = path.parent
        if not ctx.fs.exists(parent):
            ctx.fs.mkdir(parent, parents=True)
        ctx.fs.write_text(path, content)
        console.ok(f"Refreshed {rel_path}")
        return True
    except OSError as exc:
        console.err(f"Failed to write {rel_path}: {exc}")
        return False


def create_if_missing(ctx: FeatureContext, rel_path: str, content: str) -> bool:
    """Scaffold application source only if it doesn't exist yet - never touched again,
    even with --force, since this is the user's own code, not a forgepy-managed config."""
    path = ctx.cwd / rel_path
    if ctx.fs.exists(path):
        return True

    if ctx.cfg.dry_run:
        console.dry(f"Would create {rel_path}")
        return True

    try:
        parent = path.parent
        if not ctx.fs.exists(parent):
            ctx.fs.mkdir(parent, parents=True)
        ctx.fs.write_text(path, content)
        console.ok(f"Created {rel_path}")
        return True
    except OSError as exc:
        console.err(f"Failed to write {rel_path}: {exc}")
        return False


def remove_file(ctx: FeatureContext, rel_path: str) -> None:
    path = ctx.cwd / rel_path
    if not ctx.fs.exists(path):
        return

    if not ctx.cfg.force:
        console.info(f"Skipping removal of {rel_path} (use --force to delete)")
        return

    if ctx.cfg.dry_run:
        console.dry(f"Would remove {rel_path}")
        return

    try:
        ctx.fs.unlink(path)
        console.ok(f"Removed {rel_path}")
    except OSError as exc:
        console.warn(f"Failed to remove {rel_path}: {exc}")
