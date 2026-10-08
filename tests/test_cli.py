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
    assert result.returncode != 0


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
    assert mode_b in result.stderr


def test_docker_with_library_rejected(tmp_path: Path):
    result = run_cli("init", "--library", "--docker", "--dry-run", cwd=tmp_path)
    assert result.returncode != 0
    assert "docker" in result.stderr.lower()


def test_debian_with_website_rejected(tmp_path: Path):
    result = run_cli("init", "--website", "--debian", "--dry-run", cwd=tmp_path)
    assert result.returncode != 0
    assert "debian" in result.stderr.lower()


def test_dry_run_leaves_no_pyproject(tmp_path: Path):
    result = run_cli("init", "--dry-run", cwd=tmp_path)
    assert result.returncode == 0
    assert not (tmp_path / "pyproject.toml").exists()


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
    assert not (tmp_path / ".github/release.json").exists()


def test_no_all_with_explicit_testing_reenables_it(tmp_path: Path):
    result = run_cli("init", "--no-all", "--testing", cwd=tmp_path)
    assert result.returncode == 0
    assert (tmp_path / "pytest.toml").exists()
    assert not (tmp_path / "ruff.toml").exists()


def test_sync_creates_managed_configs(tmp_path: Path):
    result = run_cli("sync", cwd=tmp_path)
    assert result.returncode == 0
    assert (tmp_path / ".forgepy/ruff.toml").exists()
    assert (tmp_path / ".forgepy/pyrightconfig.json").exists()


def test_sync_check_fails_when_missing(tmp_path: Path):
    result = run_cli("sync", "--check", cwd=tmp_path)
    assert result.returncode == 1
    assert not (tmp_path / ".forgepy/ruff.toml").exists()


def test_sync_check_passes_after_sync(tmp_path: Path):
    run_cli("sync", cwd=tmp_path)
    result = run_cli("sync", "--check", cwd=tmp_path)
    assert result.returncode == 0


def test_sync_check_fails_after_tampering(tmp_path: Path):
    run_cli("sync", cwd=tmp_path)
    (tmp_path / ".forgepy/ruff.toml").write_text("tampered", encoding="utf-8")
    result = run_cli("sync", "--check", cwd=tmp_path)
    assert result.returncode == 1


def test_init_then_sync_check_passes(tmp_path: Path):
    """The .forgepy/ snapshot init writes should already match what sync expects."""
    run_cli("init", cwd=tmp_path)
    result = run_cli("sync", "--check", cwd=tmp_path)
    assert result.returncode == 0


@pytest.mark.parametrize("args", [("--library",), ("--website",), ("--docker",), ("--debian",)])
def test_jython_with_packaging_or_other_modes_rejected(tmp_path: Path, args: tuple[str, ...]):
    result = run_cli("init", "--jython", *args, "--dry-run", cwd=tmp_path)
    assert result.returncode != 0
    assert "jython" in result.stderr.lower()


def test_jython_creates_a_jython_script(tmp_path: Path):
    result = run_cli("init", "--jython", cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "src" / "hello.py").exists()
    assert (tmp_path / ".forgepy" / "ruff-jython.toml").exists()


def test_jython_without_linting_rejected(tmp_path: Path):
    result = run_cli("init", "--jython", "--no-linting", "--dry-run", cwd=tmp_path)
    assert result.returncode != 0
    assert "jython" in result.stderr.lower()


def test_check_jython_fails_on_a_comma_after_kwargs(tmp_path: Path):
    (tmp_path / "script.py").write_text("handler(\n    event,\n    **kwargs,\n)\n", encoding="utf-8")
    result = run_cli("check-jython", "script.py", cwd=tmp_path)
    assert result.returncode == 1
    assert "script.py:4" in result.stdout + result.stderr
