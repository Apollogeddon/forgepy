"""Only suite that runs real `uv sync` + generated tools; points the scaffolded
dependency at this repo since forgepy isn't on PyPI yet."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import tomlkit

REPO_ROOT = Path(__file__).resolve().parent.parent

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(shutil.which("uv") is None, reason="uv not on PATH"),
]


def _use_local_forgepy_source(pyproject_path: Path) -> None:
    doc = tomlkit.parse(pyproject_path.read_text(encoding="utf-8"))
    tool = doc.setdefault("tool", tomlkit.table())
    uv_table = tool.get("uv")
    if uv_table is None:
        uv_table = tomlkit.table()
        tool["uv"] = uv_table

    forgepy_source = tomlkit.inline_table()
    forgepy_source["path"] = REPO_ROOT.as_posix()
    forgepy_source["editable"] = True
    sources = tomlkit.table()
    sources["forgepy"] = forgepy_source
    uv_table["sources"] = sources

    pyproject_path.write_text(tomlkit.dumps(doc), encoding="utf-8")


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, (
        f"`{' '.join(args)}` in {cwd} failed (exit {result.returncode}):\n"
        f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
    )
    return result


def _scaffold(tmp_path: Path, *args: str) -> Path:
    init = subprocess.run(
        [sys.executable, "-m", "forgepy", "init", *args],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert init.returncode == 0, f"forgepy init {args} failed:\n{init.stdout}\n{init.stderr}"
    _use_local_forgepy_source(tmp_path / "pyproject.toml")
    _run(["uv", "sync"], cwd=tmp_path)
    return tmp_path


def test_backend_scaffold_passes_its_own_toolchain(tmp_path: Path):
    project = _scaffold(tmp_path, "--backend")
    _run(["uv", "run", "poe", "lint"], cwd=project)
    _run(["uv", "run", "poe", "type"], cwd=project)
    _run(["uv", "run", "poe", "test"], cwd=project)
    _run(["uv", "run", "poe", "start"], cwd=project)
    _run(["uv", "run", "poe", "build"], cwd=project)
    _run(["uv", "run", "poe", "sync-check"], cwd=project)


def test_library_scaffold_passes_its_own_toolchain(tmp_path: Path):
    project = _scaffold(tmp_path, "--library")
    _run(["uv", "run", "poe", "lint"], cwd=project)
    _run(["uv", "run", "poe", "type"], cwd=project)
    _run(["uv", "run", "poe", "test"], cwd=project)
    _run(["uv", "run", "poe", "build"], cwd=project)
    _run(["uv", "run", "poe", "check-dist"], cwd=project)


def test_website_scaffold_passes_its_own_toolchain(tmp_path: Path):
    project = _scaffold(tmp_path, "--website")
    _run(["uv", "run", "poe", "lint"], cwd=project)
    _run(["uv", "run", "poe", "type"], cwd=project)
    _run(["uv", "run", "poe", "test"], cwd=project)
    _run(["uv", "run", "poe", "build"], cwd=project)
    _run(["uv", "run", "poe", "sync-check"], cwd=project)


def test_backend_no_testing_scaffold_passes_its_own_toolchain(tmp_path: Path):
    """Regression: pyrightconfig.json used to hardcode "include": ["src", "tests"],
    crashing basedpyright when --no-testing skipped creating tests/."""
    project = _scaffold(tmp_path, "--backend", "--no-testing")
    _run(["uv", "run", "poe", "lint"], cwd=project)
    _run(["uv", "run", "poe", "type"], cwd=project)
    _run(["uv", "run", "poe", "build"], cwd=project)


def test_backend_debian_scaffold_syncs_and_validates(tmp_path: Path):
    """Doesn't invoke nfpm itself (external Go binary, not part of this toolchain)."""
    project = _scaffold(tmp_path, "--backend", "--debian")
    _run(["uv", "run", "poe", "lint"], cwd=project)
    _run(["uv", "run", "poe", "type"], cwd=project)
