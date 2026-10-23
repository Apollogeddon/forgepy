"""Only suite that runs real `uv sync` + generated tools; points the scaffolded
dependency at this repo since forgepy isn't on PyPI yet."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
import tomlkit
import yaml
from support import BASH

from forgepy.config import DEBIAN_IMAGE, DEBIAN_PYTHON_VERSION

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


def _run(
    args: list[str], cwd: Path, timeout: int = 180, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
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


# the steps in the check pipeline's stages that set up the runner rather than check the project
_RUNNER_STEPS = {"Resolve the Python version", "Run the pre-build command"}


def _run_check_stages(project: Path) -> list[str]:
    """Runs what the generated .index.yml's check pipeline runs: its lint, test and build stages' commands,
    read from this repository's pipeline with the inputs .index.yml passes, as @main serves them."""
    index = yaml.safe_load((project / ".github/workflows/.index.yml").read_text(encoding="utf-8"))
    job = next(job for name, job in index["jobs"].items() if name in ("library", "service", "website"))
    match = re.fullmatch(r"apollogeddon/forgepy/\.github/workflows/([\w-]+\.yml)@main", job["uses"])
    assert match, job["uses"]
    pipeline = yaml.safe_load((REPO_ROOT / ".github/workflows" / match.group(1)).read_text(encoding="utf-8"))
    declared = pipeline[True]["workflow_call"]["inputs"]
    inputs = {name: spec["default"] for name, spec in declared.items()} | job.get("with", {})
    env = {**os.environ, "SYNC_ARGS": inputs["sync_args"], "BUILD_COMMAND": inputs["build_command"]}
    ran: list[str] = []
    for stage in ("lint", "test", "build"):
        if pipeline["jobs"][stage].get("if") in ("inputs.run_tests", "inputs.run_build") and not inputs.get(
            pipeline["jobs"][stage]["if"].removeprefix("inputs.")
        ):
            continue
        for step in pipeline["jobs"][stage]["steps"]:
            if "run" not in step or step["name"] in _RUNNER_STEPS:
                continue
            # a step guarded on a file forgepy writes runs when the project has it
            guard = re.match(r"hashFiles\(format\('\{0\}/([^']+)'", step.get("if", ""))
            if guard and not list(project.glob(guard.group(1))):
                continue
            _run([BASH, "-e", "-c", step["run"]], cwd=project, env=env)
            ran.append(f"{stage} / {step['name']}")
    return ran


def test_backend_scaffold_passes_its_own_toolchain(tmp_path: Path):
    project = _scaffold(tmp_path, "--backend")
    # formats the scaffold, as the pre-commit hook does before its first commit reaches CI
    _run(["uv", "run", "poe", "lint"], cwd=project)
    assert "lint / Check forgepy's configs" in _run_check_stages(project)
    _run(["uv", "run", "poe", "start"], cwd=project)


def test_library_scaffold_passes_its_own_toolchain(tmp_path: Path):
    project = _scaffold(tmp_path, "--library")
    _run(["uv", "run", "poe", "lint"], cwd=project)
    assert "build / Build" in _run_check_stages(project)
    _run(["uv", "run", "poe", "check-dist"], cwd=project)


def test_website_scaffold_passes_its_own_toolchain(tmp_path: Path):
    project = _scaffold(tmp_path, "--website")
    _run(["uv", "run", "poe", "lint"], cwd=project)
    assert "build / Build" in _run_check_stages(project)
    assert (project / "dist" / "index.html").is_file()


def test_jython_scaffold_passes_its_own_toolchain(tmp_path: Path):
    project = _scaffold(tmp_path, "--jython")
    _run(["uv", "run", "poe", "lint"], cwd=project)
    ran = _run_check_stages(project)
    assert "lint / Check Jython 2.7 compatibility" in ran
    # its scripts are deployed as they are, so the build stage is off
    assert not any(step.startswith("build /") for step in ran)


def test_jython_compat_rejects_python_3_syntax(tmp_path: Path):
    project = _scaffold(tmp_path, "--jython")
    (project / "src" / "modern.py").write_text('def greet(name):\n    return f"Hello, {name}!"\n', encoding="utf-8")
    result = subprocess.run(["uv", "run", "poe", "compat"], cwd=project, capture_output=True, check=False)
    assert result.returncode != 0


def test_backend_no_testing_scaffold_passes_its_own_toolchain(tmp_path: Path):
    """Regression: pyrightconfig.json used to hardcode "include": ["src", "tests"],
    crashing basedpyright when --no-testing skipped creating tests/."""
    project = _scaffold(tmp_path, "--backend", "--no-testing")
    _run(["uv", "run", "poe", "lint"], cwd=project)
    ran = _run_check_stages(project)
    assert not any(step.startswith("test /") for step in ran)


def test_backend_debian_scaffold_syncs_and_validates(tmp_path: Path):
    """Doesn't invoke nfpm itself (external Go binary, not part of this toolchain)."""
    project = _scaffold(tmp_path, "--backend", "--debian")
    _run(["uv", "run", "poe", "lint"], cwd=project)
    _run(["uv", "run", "poe", "type"], cwd=project)


DEBIAN_PYTHON = shutil.which(f"python{DEBIAN_PYTHON_VERSION}")


@pytest.mark.skipif(DEBIAN_PYTHON is None, reason=f"no system Python {DEBIAN_PYTHON_VERSION}, {DEBIAN_IMAGE}'s")
def test_backend_debian_builds_its_venv_on_the_build_images_python(tmp_path: Path):
    """Runs debian.yml's build stage against the Python its image ships, with a stand-in for nfpm."""
    assert DEBIAN_PYTHON is not None
    project = _scaffold(tmp_path, "--backend", "--debian")
    shutil.rmtree(project / ".venv")
    env = os.environ | {"UV_PYTHON": DEBIAN_PYTHON, "UV_PYTHON_DOWNLOADS": "never"}
    _run(["uv", "venv", "--relocatable", "--no-managed-python", ".venv"], cwd=project, env=env)
    _run(["uv", "sync", "--locked", "--no-dev", "--no-editable"], cwd=project, env=env)

    bin_dir = tmp_path / "fake-bin"
    bin_dir.mkdir()
    nfpm = bin_dir / "nfpm"
    nfpm.write_text('#!/bin/sh\necho "$PYTHON_MINOR $PYTHON_NEXT_MINOR" > depends.txt\n', encoding="utf-8")
    nfpm.chmod(0o755)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    _run([DEBIAN_PYTHON, "packaging/build_deb.py"], cwd=project, env=env)
    major, minor = DEBIAN_PYTHON_VERSION.split(".")
    assert (project / "depends.txt").read_text(encoding="utf-8").split() == [
        DEBIAN_PYTHON_VERSION,
        f"{major}.{int(minor) + 1}",
    ]


# the images are Linux ones, which a Docker running Windows containers, as on GitHub's Windows runners, can't build
HAS_DOCKER = (
    shutil.which("docker") is not None
    and subprocess.run(
        ["docker", "info", "--format", "{{.OSType}}"], capture_output=True, text=True, check=False
    ).stdout.strip()
    == "linux"
)
requires_docker = pytest.mark.skipif(not HAS_DOCKER, reason="no docker running Linux containers")


@pytest.fixture
def docker_image() -> Iterator[str]:
    tag = f"forgepy-e2e:{uuid.uuid4().hex[:12]}"
    yield tag
    subprocess.run(["docker", "rmi", "-f", tag], capture_output=True, check=False)


def _vendor_forgepy_into_context(project: Path) -> None:
    """uv resolves the forgepy path source from the lockfile even when skipping it, and the
    repo-root path _scaffold uses is outside the Docker build context, so copy the repo in."""
    ignore = shutil.ignore_patterns(".git", ".venv", "*_cache", "__pycache__", "htmlcov", "dist")
    shutil.copytree(REPO_ROOT, project / "vendor" / "forgepy", ignore=ignore)
    pyproject_path = project / "pyproject.toml"
    doc = tomlkit.parse(pyproject_path.read_text(encoding="utf-8"))
    source = tomlkit.inline_table()
    source["path"] = "vendor/forgepy"
    source["editable"] = True
    doc["tool"]["uv"]["sources"]["forgepy"] = source
    pyproject_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    _run(["uv", "lock"], cwd=project)


@requires_docker
def test_backend_docker_image_builds_and_runs(tmp_path: Path, docker_image: str):
    project = _scaffold(tmp_path, "--backend", "--docker")
    _vendor_forgepy_into_context(project)
    _run(["docker", "build", "-t", docker_image, "."], cwd=project, timeout=600)
    _run(["docker", "run", "--rm", docker_image], cwd=project)


@requires_docker
def test_website_docker_image_builds(tmp_path: Path, docker_image: str):
    project = _scaffold(tmp_path, "--website", "--docker")
    _vendor_forgepy_into_context(project)
    _run(["docker", "build", "-t", docker_image, "."], cwd=project, timeout=600)
