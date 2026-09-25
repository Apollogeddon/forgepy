from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def run_cli(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "forgepy", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def test_help_exits_zero(tmp_path: Path):
    result = run_cli("--help", cwd=tmp_path)
    assert result.returncode == 0
    assert "forgepy" in result.stdout


def test_no_command_prints_help_and_exits_nonzero(tmp_path: Path):
    result = run_cli(cwd=tmp_path)
    assert result.returncode == 1


def test_version_flag(tmp_path: Path):
    result = run_cli("-V", cwd=tmp_path)
    assert result.returncode == 0
    assert "forgepy" in result.stdout


def test_unknown_flag_is_rejected(tmp_path: Path):
    result = run_cli("init", "--dockr", cwd=tmp_path)
    assert result.returncode != 0


@pytest.mark.parametrize("mode_a,mode_b", [("--backend", "--library"), ("--library", "--website")])
def test_mode_conflict_rejected(tmp_path: Path, mode_a: str, mode_b: str):
    result = run_cli("init", mode_a, mode_b, "--dry-run", cwd=tmp_path)
    assert result.returncode != 0


def test_docker_with_library_rejected(tmp_path: Path):
    result = run_cli("init", "--library", "--docker", "--dry-run", cwd=tmp_path)
    assert result.returncode != 0


def test_debian_with_website_rejected(tmp_path: Path):
    result = run_cli("init", "--website", "--debian", "--dry-run", cwd=tmp_path)
    assert result.returncode != 0


def test_dry_run_leaves_no_pyproject(tmp_path: Path):
    result = run_cli("init", "--dry-run", cwd=tmp_path)
    assert result.returncode == 0
    assert not (tmp_path / "pyproject.toml").exists()
    assert "DRY RUN" in result.stdout


def test_init_creates_pyproject(tmp_path: Path):
    result = run_cli("init", cwd=tmp_path)
    assert result.returncode == 0
    assert (tmp_path / "pyproject.toml").exists()
    assert (tmp_path / "ruff.toml").exists()


def test_no_testing_actually_disables_testing_feature(tmp_path: Path):
    result = run_cli("init", "--no-testing", cwd=tmp_path)
    assert result.returncode == 0
    assert not (tmp_path / "pytest.toml").exists()


def test_no_all_disables_standard_features(tmp_path: Path):
    result = run_cli("init", "--no-all", cwd=tmp_path)
    assert result.returncode == 0
    assert not (tmp_path / "pytest.toml").exists()
    assert not (tmp_path / "ruff.toml").exists()
    assert not (tmp_path / "release-please-config.json").exists()


def test_no_all_with_explicit_testing_reenables_it(tmp_path: Path):
    result = run_cli("init", "--no-all", "--testing", cwd=tmp_path)
    assert result.returncode == 0
    assert (tmp_path / "pytest.toml").exists()
    assert not (tmp_path / "ruff.toml").exists()
