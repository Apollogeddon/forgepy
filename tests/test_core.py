from __future__ import annotations

import json
from pathlib import Path

import pytest
import tomlkit
import yaml

from forgepy.config import InitConfig, Mode
from forgepy.core import EXIT_INVALID_CONFIG, init
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
        ".github/release.json",
        ".github/.release.json",
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
    assert "uv sync" in dockerfile
    assert "ARG UV_VERSION=" in dockerfile
    assert "USER app" in dockerfile


@pytest.mark.parametrize(
    ("mode", "debian", "job"),
    [(Mode.BACKEND, False, "service"), (Mode.WEBSITE, False, "website"), (Mode.BACKEND, True, "debian")],
)
def test_init_docker_adds_docker_job_after_pipeline(mode: Mode, debian: bool, job: str):
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, mode=mode, debian=debian, docker=True), fs)
    workflow = yaml.safe_load(fs.read_text(PROJECT / ".github/workflows/index.yml"))
    docker = workflow["jobs"]["docker"]
    assert "/docker.yml@" in docker["uses"]
    assert docker["needs"] == job
    assert docker["permissions"]["packages"] == "write"
    assert f"needs.{job}.outputs.version" in docker["with"]["version"]


def test_init_without_docker_has_no_docker_job():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    workflow = yaml.safe_load(fs.read_text(PROJECT / ".github/workflows/index.yml"))
    assert list(workflow["jobs"]) == ["service"]


def test_init_website_docker_creates_nginx_dockerfile():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, mode=Mode.WEBSITE, docker=True)
    assert init(cfg, fs) == 0
    dockerfile = fs.read_text(PROJECT / "Dockerfile")
    assert "nginx" in dockerfile
    assert "zensical build" in dockerfile
    # the static site is built once on the build host; only nginx is per target platform
    assert "FROM --platform=$BUILDPLATFORM" in dockerfile


def test_init_rejects_invalid_combinations_without_writing():
    fs = MemoryFileSystem()
    assert init(InitConfig(target=PROJECT, mode=Mode.LIBRARY, docker=True), fs) == EXIT_INVALID_CONFIG
    assert not fs.exists(PROJECT / "pyproject.toml")


def test_init_always_adds_toolchain_from_git_even_without_linting():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, linting=False), fs)
    doc = tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))
    assert "forgepy[toolchain]" in list(doc["dependency-groups"]["dev"])
    assert doc["tool"]["uv"]["sources"]["forgepy"]["git"].startswith("https://github.com/")


def test_init_keeps_an_existing_forgepy_source_even_with_force():
    fs = MemoryFileSystem()
    existing = '[project]\nname = "project"\n\n[tool.uv.sources]\nforgepy = { path = "../forgepy" }\n'
    fs.write_text(PROJECT / "pyproject.toml", existing)
    init(InitConfig(target=PROJECT, force=True), fs)
    doc = tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))
    assert doc["tool"]["uv"]["sources"]["forgepy"]["path"] == "../forgepy"


def test_init_backend_has_uv_build_system():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    doc = tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))
    assert doc["build-system"]["build-backend"] == "uv_build"


def test_init_website_has_no_build_system():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, mode=Mode.WEBSITE), fs)
    assert "build-system" not in tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))


@pytest.mark.parametrize(
    ("cfg", "key"),
    [
        (InitConfig(target=PROJECT, testing=False), "run_tests"),
        (InitConfig(target=PROJECT, versioning=False), "enable_versioning"),
    ],
)
def test_init_disabled_features_switch_off_pipeline_steps(cfg: InitConfig, key: str):
    fs = MemoryFileSystem()
    init(cfg, fs)
    workflow = yaml.safe_load(fs.read_text(PROJECT / ".github/workflows/index.yml"))
    assert workflow["jobs"]["service"]["with"][key] is False


def test_init_docker_disabled_removes_dockerfile_with_force():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, docker=True), fs)
    assert fs.exists(PROJECT / "Dockerfile")

    init(InitConfig(target=PROJECT, docker=False, force=True), fs)
    assert not fs.exists(PROJECT / "Dockerfile")


def test_init_website_creates_site_scaffold():
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


def test_pyrightconfig_include_omits_src_for_website():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, mode=Mode.WEBSITE), fs)
    content = json.loads(fs.read_text(PROJECT / "pyrightconfig.json"))
    assert "src" not in content["include"]
    assert "tests" in content["include"]


def test_pyrightconfig_include_omits_tests_when_testing_disabled():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, testing=False), fs)
    content = json.loads(fs.read_text(PROJECT / "pyrightconfig.json"))
    assert "tests" not in content["include"]
    assert "src" in content["include"]


def test_pyrightconfig_include_has_both_for_default_backend():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    content = json.loads(fs.read_text(PROJECT / "pyrightconfig.json"))
    assert {"src", "tests"} <= set(content["include"])


def test_init_release_config_bumps_the_normalized_name_in_uv_lock():
    fs = MemoryFileSystem()
    fs.write_text(PROJECT / "pyproject.toml", '[project]\nname = "My_Project"\n')
    init(InitConfig(target=PROJECT), fs)
    config = json.loads(fs.read_text(PROJECT / ".github/release.json"))
    [extra] = config["packages"]["."]["extra-files"]
    assert extra["path"] == "uv.lock"
    # release-please's TOML parser wraps each value, and uv.lock records the PEP 503 normalized name;
    # with @.name=='...' or the declared name, release-please matches nothing and the lock never moves
    assert extra["jsonpath"] == "$.package[?(@.name.value=='my-project')].version"


@pytest.mark.parametrize(
    "cfg",
    [
        InitConfig(target=PROJECT),
        InitConfig(target=PROJECT, mode=Mode.LIBRARY),
        InitConfig(target=PROJECT, mode=Mode.WEBSITE),
        InitConfig(target=PROJECT, debian=True),
        InitConfig(target=PROJECT, docker=True),
    ],
    ids=["backend", "library", "website", "debian", "docker"],
)
def test_init_generates_least_privilege_ci_that_never_cancels_main(cfg: InitConfig):
    fs = MemoryFileSystem()
    init(cfg, fs)
    workflow = yaml.safe_load(fs.read_text(PROJECT / ".github/workflows/index.yml"))
    assert "refs/heads/main" in workflow["concurrency"]["cancel-in-progress"]
    for name, job in workflow["jobs"].items():
        # the called workflows only use GITHUB_TOKEN, which they get without inheriting every secret
        assert "secrets" not in job, f"{name} passes secrets"
        # only PyPI trusted publishing and GitHub Pages need an OIDC token
        if name not in ("library", "website"):
            assert "id-token" not in job.get("permissions", {}), f"{name} asks for id-token"
