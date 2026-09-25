from __future__ import annotations

from pathlib import Path

import tomlkit

from forgepy.config import InitConfig, Mode
from forgepy.core import init
from forgepy.utils.filesystem import MemoryFileSystem

PROJECT = Path("project")


def test_init_creates_expected_files_for_backend():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT)
    assert init(cfg, fs) == 0

    for expected in (
        "pyproject.toml",
        ".python-version",
        "ruff.toml",
        ".forgepy/ruff.toml",
        "pyrightconfig.json",
        ".forgepy/pyrightconfig.json",
        ".pre-commit-config.yaml",
        "pytest.toml",
        "release-please-config.json",
        ".release-please-manifest.json",
    ):
        assert fs.exists(PROJECT / expected), f"expected {expected} to exist"


def test_init_library_has_no_private_classifier():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, mode=Mode.LIBRARY)
    init(cfg, fs)

    doc = tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))
    assert "classifiers" not in doc["project"]


def test_init_backend_has_private_classifier():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, mode=Mode.BACKEND)
    init(cfg, fs)

    doc = tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))
    assert "Private :: Do Not Upload" in list(doc["project"]["classifiers"])


def test_init_does_not_overwrite_without_force():
    fs = MemoryFileSystem()
    fs.write_text(PROJECT / "ruff.toml", "custom content")
    cfg = InitConfig(target=PROJECT)
    init(cfg, fs)
    assert fs.read_text(PROJECT / "ruff.toml") == "custom content"


def test_init_overwrites_with_force():
    fs = MemoryFileSystem()
    fs.write_text(PROJECT / "ruff.toml", "custom content")
    cfg = InitConfig(target=PROJECT, force=True)
    init(cfg, fs)
    assert fs.read_text(PROJECT / "ruff.toml") != "custom content"


def test_init_dry_run_writes_nothing():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, dry_run=True)
    init(cfg, fs)
    assert not fs.exists(PROJECT / "pyproject.toml")
    assert not fs.exists(PROJECT / "ruff.toml")


def test_init_disabling_linting_removes_linting_files_with_force():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    assert fs.exists(PROJECT / "ruff.toml")

    init(InitConfig(target=PROJECT, linting=False, force=True), fs)
    assert not fs.exists(PROJECT / "ruff.toml")
    assert not fs.exists(PROJECT / ".forgepy/ruff.toml")


def test_init_disabling_linting_without_force_keeps_files():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    init(InitConfig(target=PROJECT, linting=False), fs)
    assert fs.exists(PROJECT / "ruff.toml")


def test_init_reports_error_on_malformed_pyproject():
    fs = MemoryFileSystem()
    fs.write_text(PROJECT / "pyproject.toml", "not [ valid")
    cfg = InitConfig(target=PROJECT)
    assert init(cfg, fs) == 1


def test_init_backend_docker_creates_uv_based_dockerfile():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, docker=True)
    assert init(cfg, fs) == 0
    dockerfile = fs.read_text(PROJECT / "Dockerfile")
    assert "astral-sh/uv" in dockerfile
    assert "distroless" not in dockerfile


def test_init_website_docker_creates_nginx_dockerfile():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, mode=Mode.WEBSITE, docker=True)
    assert init(cfg, fs) == 0
    dockerfile = fs.read_text(PROJECT / "Dockerfile")
    assert "nginx" in dockerfile
    assert "mkdocs build" in dockerfile


def test_init_docker_disabled_removes_dockerfile_with_force():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, docker=True), fs)
    assert fs.exists(PROJECT / "Dockerfile")

    init(InitConfig(target=PROJECT, docker=False, force=True), fs)
    assert not fs.exists(PROJECT / "Dockerfile")


def test_init_website_creates_mkdocs_scaffold():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, mode=Mode.WEBSITE)
    assert init(cfg, fs) == 0
    assert fs.exists(PROJECT / "mkdocs.yml")
    assert fs.exists(PROJECT / "docs/index.md")


def test_init_website_generates_website_workflow():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, mode=Mode.WEBSITE)
    init(cfg, fs)
    content = fs.read_text(PROJECT / ".github/workflows/index.yml")
    assert "website.yml@main" in content


def test_init_debian_creates_packaging_files():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, debian=True)
    assert init(cfg, fs) == 0
    assert fs.exists(PROJECT / "nfpm.yaml")
    assert fs.exists(PROJECT / "packaging/project.service")
    assert fs.exists(PROJECT / "packaging/postinstall.sh")
    content = fs.read_text(PROJECT / ".github/workflows/index.yml")
    assert "debian.yml@main" in content


def test_init_debian_disabled_removes_packaging_files_with_force():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, debian=True), fs)
    assert fs.exists(PROJECT / "nfpm.yaml")

    init(InitConfig(target=PROJECT, debian=False, force=True), fs)
    assert not fs.exists(PROJECT / "nfpm.yaml")
    assert not fs.exists(PROJECT / "packaging/project.service")


def test_debian_rejected_outside_backend_mode():
    errors = InitConfig(mode=Mode.WEBSITE, debian=True).validate()
    assert any("debian" in e for e in errors)
