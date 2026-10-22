from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

import pytest
import tomlkit
import yaml

from forgepy.config import InitConfig, Mode
from forgepy.core import EXIT_INVALID_CONFIG, init
from forgepy.features import base
from forgepy.features.base import FORGEPY_GIT, release_tag
from forgepy.utils.filesystem import MemoryFileSystem

PROJECT = Path("project")
COOLDOWN_DAYS = 3
INDEX = PROJECT / ".github/workflows/.index.yml"
FORGEPY = "apollogeddon/forgepy/.github/workflows"


def _workflow(fs: MemoryFileSystem) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(fs.read_text(INDEX)))


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
    ("mode", "debian", "checks"),
    [(Mode.BACKEND, False, "service"), (Mode.WEBSITE, False, "website"), (Mode.BACKEND, True, "service")],
)
def test_init_docker_adds_docker_job_after_the_checks(mode: Mode, *, debian: bool, checks: str):
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, mode=mode, debian=debian, docker=True), fs)
    docker = _workflow(fs)["jobs"]["docker"]
    assert docker["uses"] == f"{FORGEPY}/docker.yml@main"
    assert docker["needs"] == ["version", checks]
    assert docker["permissions"]["packages"] == "write"
    assert docker["with"]["version"] == "${{ needs.version.outputs.version }}"


def test_init_without_docker_has_no_docker_job():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    assert list(_workflow(fs)["jobs"]) == ["version", "service", "patch", "merge"]


def test_init_packages_a_debian_backend_after_its_checks_and_attaches_it_to_the_release():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, debian=True), fs)
    jobs = _workflow(fs)["jobs"]
    assert jobs["service"]["uses"] == f"{FORGEPY}/service.yml@main"
    assert jobs["debian"]["needs"] == "service"
    assert jobs["publish"]["with"]["assets"] == "debian-package"


def test_init_website_docker_creates_nginx_dockerfile():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, mode=Mode.WEBSITE, docker=True)
    assert init(cfg, fs) == 0
    dockerfile = fs.read_text(PROJECT / "Dockerfile")
    assert "nginx" in dockerfile
    assert "zensical build" in dockerfile
    # the static site is built once on the build host; only nginx is per target platform
    assert "FROM --platform=$BUILDPLATFORM" in dockerfile


@pytest.mark.parametrize("mode", [Mode.BACKEND, Mode.LIBRARY])
@pytest.mark.parametrize(("windows", "macos"), [(True, False), (False, True), (True, True)])
def test_init_tests_and_builds_on_windows_and_macos_when_asked(mode: Mode, *, windows: bool, macos: bool):
    fs = MemoryFileSystem()
    assert init(InitConfig(target=PROJECT, mode=mode, windows=windows, macos=macos), fs) == 0
    checks = _workflow(fs)["jobs"]["library" if mode.is_library else "service"]
    expected = {"test_windows": "windows-latest"} if windows else {}
    expected |= {"test_macos": "macos-latest"} if macos else {}
    assert {k: v for k, v in checks.get("with", {}).items() if k.startswith("test_")} == expected


def test_init_leaves_windows_and_macos_off_by_default():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    assert "with" not in _workflow(fs)["jobs"]["service"]


@pytest.mark.parametrize("flag", ["windows", "macos"])
def test_init_refuses_windows_and_macos_for_a_website(flag: str):
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, mode=Mode.WEBSITE, windows=flag == "windows", macos=flag == "macos")
    assert cfg.validate() == [f"--{flag} is not available in website mode"]
    assert init(cfg, fs) == EXIT_INVALID_CONFIG
    assert not fs.exists(PROJECT / "pyproject.toml")


def test_init_rejects_invalid_combinations_without_writing():
    fs = MemoryFileSystem()
    assert init(InitConfig(target=PROJECT, mode=Mode.LIBRARY, docker=True), fs) == EXIT_INVALID_CONFIG
    assert not fs.exists(PROJECT / "pyproject.toml")


@pytest.mark.parametrize("version", ["banana", "3", "3.9", "2.7", "3.13.x", ">=3.13", ""])
def test_init_rejects_an_invalid_python_version_without_writing(version: str):
    fs = MemoryFileSystem()
    assert init(InitConfig(target=PROJECT, python_version=version), fs) == EXIT_INVALID_CONFIG
    assert not fs.exists(PROJECT / "pyproject.toml")


def test_init_takes_a_patch_python_version_and_targets_its_minor_in_ruff():
    fs = MemoryFileSystem()
    assert init(InitConfig(target=PROJECT, python_version="3.12.4"), fs) == 0
    assert fs.read_text(PROJECT / ".python-version") == "3.12.4\n"
    assert 'target-version = "py312"' in fs.read_text(PROJECT / "ruff.toml")


def test_init_in_a_directory_with_spaces_makes_a_valid_package():
    fs = MemoryFileSystem()
    target = Path("My Project")
    assert init(InitConfig(target=target), fs) == 0
    doc = tomlkit.parse(fs.read_text(target / "pyproject.toml"))
    assert doc["project"]["name"] == "my-project"
    assert fs.exists(target / "src/my_project/__init__.py")


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


def _forgepy_source(fs: MemoryFileSystem) -> dict[str, object]:
    doc = tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))
    return dict(doc["tool"]["uv"]["sources"]["forgepy"])


def test_init_pins_the_forgepy_source_to_the_running_release(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(base, "__version__", "1.2.3")
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    assert _forgepy_source(fs) == {"git": FORGEPY_GIT, "tag": "v1.2.3"}


# projects track the pipelines at main on purpose, whichever forgepy release ran init
@pytest.mark.parametrize("version", ["1.2.3", "1.3.0.dev0"])
def test_init_calls_the_pipelines_at_main(monkeypatch: pytest.MonkeyPatch, version: str):
    monkeypatch.setattr(base, "__version__", version)
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    uses = [job["uses"] for job in _workflow(fs)["jobs"].values()]
    assert uses
    assert all(use.endswith(".yml@main") for use in uses)


def test_init_leaves_the_forgepy_source_untagged_for_a_build_that_isnt_a_release(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    monkeypatch.setattr(base, "__version__", "1.3.0.dev0")
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    assert _forgepy_source(fs) == {"git": FORGEPY_GIT}
    assert "isn't a release" in capsys.readouterr().out


@pytest.mark.parametrize(("version", "tag"), [("0.7.0", "v0.7.0"), ("10.20.30", "v10.20.30")])
def test_release_tag_for_a_release(version: str, tag: str):
    assert release_tag(version) == tag


@pytest.mark.parametrize("version", ["0.8.0.dev1", "0.8.0rc1", "0.7.0+g1234abc", "0.7"])
def test_release_tag_is_none_for_other_versions(version: str):
    assert release_tag(version) is None


@pytest.mark.parametrize("force", [False, True])
def test_init_tags_an_existing_untagged_forgepy_source(monkeypatch: pytest.MonkeyPatch, *, force: bool):
    monkeypatch.setattr(base, "__version__", "1.2.3")
    fs = MemoryFileSystem()
    existing = f'[project]\nname = "project"\n\n[tool.uv.sources]\nforgepy = {{ git = "{FORGEPY_GIT}" }}\n'
    fs.write_text(PROJECT / "pyproject.toml", existing)
    init(InitConfig(target=PROJECT, force=force), fs)
    assert _forgepy_source(fs) == {"git": FORGEPY_GIT, "tag": "v1.2.3"}


def test_init_keeps_an_existing_forgepy_tag_without_force(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(base, "__version__", "1.2.3")
    fs = MemoryFileSystem()
    existing = (
        f'[project]\nname = "project"\n\n[tool.uv.sources]\nforgepy = {{ git = "{FORGEPY_GIT}", tag = "v1.0.0" }}\n'
    )
    fs.write_text(PROJECT / "pyproject.toml", existing)
    init(InitConfig(target=PROJECT), fs)
    assert _forgepy_source(fs)["tag"] == "v1.0.0"

    init(InitConfig(target=PROJECT, force=True), fs)
    assert _forgepy_source(fs)["tag"] == "v1.2.3"


@pytest.mark.parametrize(
    "source",
    [
        f'{{ git = "{FORGEPY_GIT}", branch = "next" }}',
        f'{{ git = "{FORGEPY_GIT}", rev = "abc1234" }}',
        '{ git = "https://github.com/someone/forgepy-fork" }',
    ],
)
def test_init_keeps_a_forgepy_branch_rev_or_fork_even_with_force(monkeypatch: pytest.MonkeyPatch, source: str):
    monkeypatch.setattr(base, "__version__", "1.2.3")
    fs = MemoryFileSystem()
    fs.write_text(PROJECT / "pyproject.toml", f'[project]\nname = "project"\n\n[tool.uv.sources]\nforgepy = {source}\n')
    init(InitConfig(target=PROJECT, force=True), fs)
    assert "tag" not in _forgepy_source(fs)


def test_init_backend_has_uv_build_system():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    doc = tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))
    assert doc["build-system"]["build-backend"] == "uv_build"


def test_init_website_has_no_build_system():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, mode=Mode.WEBSITE), fs)
    assert "build-system" not in tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))


def test_init_no_testing_switches_off_the_test_stage():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, testing=False), fs)
    assert _workflow(fs)["jobs"]["service"]["with"]["run_tests"] is False


def test_init_no_versioning_leaves_out_the_version_job():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, versioning=False), fs)
    jobs = _workflow(fs)["jobs"]
    # without versioning there's no release to wait for, so the checks run on every push
    assert "version" not in jobs
    assert "needs" not in jobs["service"]


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
    jobs = _workflow(fs)["jobs"]
    assert jobs["website"]["uses"] == f"{FORGEPY}/website.yml@main"
    assert jobs["pages"]["uses"] == f"{FORGEPY}/pages.yml@main"


def test_init_debian_creates_packaging_files():
    fs = MemoryFileSystem()
    cfg = InitConfig(target=PROJECT, debian=True)
    assert init(cfg, fs) == 0
    assert fs.exists(PROJECT / "nfpm.yaml")
    assert fs.exists(PROJECT / "packaging/project.service")
    assert fs.exists(PROJECT / "packaging/postinstall.sh")
    assert _workflow(fs)["jobs"]["debian"]["uses"] == f"{FORGEPY}/debian.yml@main"


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
        InitConfig(target=PROJECT, windows=True, macos=True),
        InitConfig(target=PROJECT, mode=Mode.LIBRARY, windows=True, macos=True),
    ],
    ids=["backend", "library", "website", "debian", "docker", "windows-macos", "library-windows-macos"],
)
def test_init_generates_least_privilege_ci_that_never_cancels_main(cfg: InitConfig):
    fs = MemoryFileSystem()
    init(cfg, fs)
    workflow = _workflow(fs)
    # a run outside a pull request has a group of its own, so one on main is never cancelled
    assert "github.event.pull_request.number || github.run_id" in workflow["concurrency"]["group"]
    assert workflow["permissions"] == {}
    for name, job in workflow["jobs"].items():
        # secrets go by name, never inherit, and only the release app's key at that
        assert job.get("secrets", {}) in ({}, {"APP_PRIVATE_KEY": "${{ secrets.RELEASE_APP_PRIVATE_KEY }}"}), name
        # only PyPI Trusted Publishing and GitHub Pages need an OIDC token
        if name not in ("publish", "pages"):
            assert "id-token" not in job["permissions"], f"{name} asks for id-token"
    # forgepy's files are refreshed through a pull request, weekly, on a manual run and after a Dependabot merge
    assert workflow["jobs"]["patch"]["uses"] == f"{FORGEPY}/patch.yml@main"


def test_init_jython_installs_only_the_dev_tools():
    fs = MemoryFileSystem()
    assert init(InitConfig(target=PROJECT, jython=True), fs) == 0

    doc = tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))
    assert "build-system" not in doc
    assert doc["tool"]["uv"]["package"] is False
    assert "build" not in doc["tool"]["poe"]["tasks"]
    assert "start" not in doc["tool"]["poe"]["tasks"]
    assert fs.exists(PROJECT / "src/hello.py")
    assert not fs.exists(PROJECT / "src/project/__init__.py")


def test_init_jython_script_avoids_python_3_syntax():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, jython=True), fs)
    script = fs.read_text(PROJECT / "src/hello.py")
    assert "# type: (Optional[str]) -> str" in script
    assert ".format(" in script
    assert 'f"' not in script


def test_init_jython_lints_against_the_jython_base():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, jython=True), fs)

    ruff = fs.read_text(PROJECT / "ruff.toml")
    assert ruff.startswith('extend = ".forgepy/ruff-jython.toml"\n')
    assert ruff.endswith('[per-file-target-version]\n"tests/**" = "py313"\n')
    base = tomlkit.parse(fs.read_text(PROJECT / ".forgepy/ruff-jython.toml"))
    assert base["extend"] == "ruff.toml"
    assert {"UP", "PTH", "F401"} <= set(base["lint"]["ignore"])

    pyright = json.loads(fs.read_text(PROJECT / "pyrightconfig.json"))
    assert pyright["defineConstant"] == {"MYPY": True}
    assert pyright["reportTypeCommentUsage"] is False

    assert 'pythonpath = ["src"]' in fs.read_text(PROJECT / "pytest.toml")


def test_init_jython_checks_compatibility_with_vermin():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, jython=True), fs)

    doc = tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))
    assert any(str(dep).startswith("vermin") for dep in doc["dependency-groups"]["dev"])
    compat = doc["tool"]["poe"]["tasks"]["compat"]["shell"]
    assert "--target=2.7-" in compat
    assert "forgepy check-jython src" in compat
    hooks = yaml.safe_load(fs.read_text(PROJECT / ".pre-commit-config.yaml"))["repos"][0]["hooks"]
    assert any(hook["id"] == "vermin" for hook in hooks)


def test_init_jython_workflow_skips_the_build():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, jython=True), fs)
    assert _workflow(fs)["jobs"]["service"]["with"]["run_build"] is False


def test_init_without_jython_has_no_jython_files():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    assert not fs.exists(PROJECT / ".forgepy/ruff-jython.toml")
    doc = tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))
    assert "compat" not in doc["tool"]["poe"]["tasks"]
    assert "defineConstant" not in json.loads(fs.read_text(PROJECT / "pyrightconfig.json"))


def test_init_without_jython_removes_the_jython_base_with_force():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, jython=True), fs)
    init(InitConfig(target=PROJECT, force=True), fs)
    assert not fs.exists(PROJECT / ".forgepy/ruff-jython.toml")


def test_init_writes_editorconfig_and_dependabot_with_a_cooldown():
    fs = MemoryFileSystem()
    assert init(InitConfig(target=PROJECT), fs) == 0
    assert "[*.py]\nindent_size = 4" in fs.read_text(PROJECT / ".editorconfig")

    dependabot = yaml.safe_load(fs.read_text(PROJECT / ".github/dependabot.yml"))
    assert [u["package-ecosystem"] for u in dependabot["updates"]] == ["uv", "github-actions"]
    assert all(u["cooldown"]["default-days"] == COOLDOWN_DAYS for u in dependabot["updates"])
    # the pipelines are called at @main, which has no versions to propose
    assert dependabot["updates"][1]["ignore"] == [{"dependency-name": "apollogeddon/forgepy"}]


def test_init_docker_adds_docker_to_dependabot():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT, docker=True), fs)
    dependabot = yaml.safe_load(fs.read_text(PROJECT / ".github/dependabot.yml"))
    assert "docker" in [u["package-ecosystem"] for u in dependabot["updates"]]


def test_init_codeowners_names_the_github_remote_owner_and_needs_one():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    assert not fs.exists(PROJECT / ".github/CODEOWNERS")

    fs = MemoryFileSystem({str(PROJECT / ".git/config"): '[remote "origin"]\n\turl = git@github.com:acme/widget.git\n'})
    init(InitConfig(target=PROJECT), fs)
    assert "* @acme\n" in fs.read_text(PROJECT / ".github/CODEOWNERS")


def test_init_codeowners_prefers_the_project_urls():
    fs = MemoryFileSystem(
        {
            str(PROJECT / "pyproject.toml"): (
                '[project]\nname = "widget"\nversion = "0.1.0"\n\n'
                '[project.urls]\nRepository = "https://github.com/octo-org/widget"\n'
            ),
            str(PROJECT / ".git/config"): '[remote "origin"]\n\turl = git@github.com:acme/widget.git\n',
        }
    )
    init(InitConfig(target=PROJECT), fs)
    assert "* @octo-org\n" in fs.read_text(PROJECT / ".github/CODEOWNERS")


class _CountingFileSystem(MemoryFileSystem):
    def __init__(self) -> None:
        super().__init__()
        self.writes: list[Path] = []

    def write_text(self, path: Path, content: str) -> None:
        self.writes.append(path)
        super().write_text(path, content)


def test_init_leaves_unchanged_managed_files_alone():
    fs = _CountingFileSystem()
    assert init(InitConfig(target=PROJECT), fs) == 0
    fs.writes.clear()
    assert init(InitConfig(target=PROJECT), fs) == 0
    assert not [path for path in fs.writes if ".forgepy" in path.parts]


def test_init_writes_a_gitignore_once_and_keeps_the_projects_own():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    ignore = fs.read_text(PROJECT / ".gitignore")
    for entry in (".venv/", "dist/", "junit-report.xml", "coverage.json"):
        assert entry in ignore
    fs.write_text(PROJECT / ".gitignore", "custom\n")
    init(InitConfig(target=PROJECT, force=True), fs)
    assert fs.read_text(PROJECT / ".gitignore") == "custom\n"


# LF on every platform, so a Windows checkout reads the same; a project's own rules are never replaced
def test_init_writes_a_gitattributes_once_and_keeps_the_projects_own():
    fs = MemoryFileSystem()
    init(InitConfig(target=PROJECT), fs)
    assert fs.read_text(PROJECT / ".gitattributes") == "* text=auto eol=lf\n"
    fs.write_text(PROJECT / ".gitattributes", "*.psd filter=lfs diff=lfs merge=lfs -text\n")
    init(InitConfig(target=PROJECT, force=True), fs)
    assert fs.read_text(PROJECT / ".gitattributes") == "*.psd filter=lfs diff=lfs merge=lfs -text\n"


def _ruff_target(fs: MemoryFileSystem) -> str:
    return tomlkit.parse(fs.read_text(PROJECT / "ruff.toml"))["target-version"]


def test_init_keeps_the_projects_python_version_file():
    fs = MemoryFileSystem()
    fs.write_text(PROJECT / ".python-version", "# pinned\n3.11\n")
    fs.write_text(PROJECT / "pyproject.toml", '[project]\nname = "app"\nrequires-python = ">=3.11"\n')
    assert init(InitConfig(target=PROJECT, docker=True), fs) == 0
    assert _ruff_target(fs) == "py311"
    assert "FROM python:3.11-slim" in fs.read_text(PROJECT / "Dockerfile")
    assert tomlkit.parse(fs.read_text(PROJECT / "pyproject.toml"))["project"]["requires-python"] == ">=3.11"


@pytest.mark.parametrize("requires", [">=3.11", ">=3.11,<4", "<4, >= 3.11", "~=3.11", "==3.11.*"])
def test_init_without_a_python_version_file_targets_requires_pythons_floor(requires: str):
    fs = MemoryFileSystem()
    fs.write_text(PROJECT / "pyproject.toml", f'[project]\nname = "app"\nrequires-python = "{requires}"\n')
    assert init(InitConfig(target=PROJECT), fs) == 0
    assert _ruff_target(fs) == "py311"
    assert fs.read_text(PROJECT / ".python-version") == "3.11\n"


def test_init_python_flag_overrides_the_projects_pin():
    fs = MemoryFileSystem()
    fs.write_text(PROJECT / ".python-version", "3.11\n")
    assert init(InitConfig(target=PROJECT, python_version="3.12"), fs) == 0
    assert _ruff_target(fs) == "py312"


@pytest.mark.parametrize("pin", ["3.9", "pypy@3.10"])
def test_init_rejects_a_project_pin_it_cant_target_without_writing(pin: str):
    fs = MemoryFileSystem()
    fs.write_text(PROJECT / ".python-version", f"{pin}\n")
    assert init(InitConfig(target=PROJECT), fs) == EXIT_INVALID_CONFIG
    assert not fs.exists(PROJECT / "pyproject.toml")


def test_init_website_docker_tags_uvs_image_by_minor_version():
    fs = MemoryFileSystem()
    assert init(InitConfig(target=PROJECT, mode=Mode.WEBSITE, docker=True, python_version="3.13.1"), fs) == 0
    assert "ghcr.io/astral-sh/uv:python3.13-bookworm-slim" in fs.read_text(PROJECT / "Dockerfile")


def test_init_debian_rejects_a_python_newer_than_its_build_image():
    fs = MemoryFileSystem()
    assert init(InitConfig(target=PROJECT, debian=True, python_version="3.14"), fs) == EXIT_INVALID_CONFIG
    assert not fs.exists(PROJECT / "pyproject.toml")
    fs.write_text(PROJECT / ".python-version", "3.14\n")
    assert init(InitConfig(target=PROJECT, debian=True), fs) == EXIT_INVALID_CONFIG


def test_init_debian_depends_on_the_python_the_venv_was_built_with(tmp_path: Path):
    """build_deb.py stamps nfpm.yaml's python3 range from .venv, whose packages only run on its minor."""
    fs = MemoryFileSystem()
    assert init(InitConfig(target=PROJECT, debian=True), fs) == 0
    depends = yaml.safe_load(fs.read_text(PROJECT / "nfpm.yaml"))["depends"]
    assert depends == ["python3 (>= ${PYTHON_MINOR})", "python3 (<< ${PYTHON_NEXT_MINOR})"]

    (tmp_path / "packaging").mkdir()
    (tmp_path / "packaging/build_deb.py").write_text(fs.read_text(PROJECT / "packaging/build_deb.py"))
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n')
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv/pyvenv.cfg").write_text("home = /usr/bin\nversion_info = 3.13.5\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # a stand-in Windows can run too, as shutil.which only finds a file with a PATHEXT extension there
    if os.name == "nt":
        (bin_dir / "nfpm.bat").write_text("@echo %VERSION% %PYTHON_MINOR% %PYTHON_NEXT_MINOR%> stamped\n")
    else:
        nfpm = bin_dir / "nfpm"
        nfpm.write_text('#!/bin/sh\necho "$VERSION $PYTHON_MINOR $PYTHON_NEXT_MINOR" > stamped\n')
        nfpm.chmod(0o755)
    env = os.environ | {"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    result = subprocess.run(
        [sys.executable, "packaging/build_deb.py"], cwd=tmp_path, env=env, check=False, capture_output=True
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "stamped").read_text().split() == ["1.2.3", "3.13", "3.14"]


class TestOldIndexWorkflow:
    """An index.yml an earlier forgepy generated, which .index.yml replaces."""

    old = PROJECT / ".github/workflows/index.yml"
    legacy = (Path(__file__).parent / "fixtures/legacy/backend.yml").read_text(encoding="utf-8")
    changed = legacy.replace("    with:\n", "    with:\n      runs_on: xerus\n")

    def _fs(self, content: str) -> MemoryFileSystem:
        fs = MemoryFileSystem()
        fs.mkdir(self.old.parent, parents=True)
        fs.write_text(self.old, content)
        return fs

    def test_is_removed_when_its_exactly_as_init_wrote_it(self, capsys: pytest.CaptureFixture[str]):
        fs = self._fs(self.legacy)
        assert init(InitConfig(target=PROJECT), fs) == 0
        assert not fs.exists(self.old)
        assert fs.exists(INDEX)
        assert "Removed .github/workflows/index.yml" in capsys.readouterr().out

    def test_is_kept_with_a_warning_once_its_been_changed(self, capsys: pytest.CaptureFixture[str]):
        fs = self._fs(self.changed)
        assert init(InitConfig(target=PROJECT), fs) == 0
        assert fs.read_text(self.old) == self.changed
        out = capsys.readouterr().out
        assert "has been changed since init wrote it" in out
        assert "use --force to delete" in out

    def test_is_removed_with_force_once_its_been_changed(self):
        fs = self._fs(self.changed)
        assert init(InitConfig(target=PROJECT, force=True), fs) == 0
        assert not fs.exists(self.old)

    def test_is_kept_on_a_dry_run(self):
        fs = self._fs(self.legacy)
        assert init(InitConfig(target=PROJECT, dry_run=True), fs) == 0
        assert fs.exists(self.old)

    # without a new workflow written, removing the old one would leave the project with no CI
    def test_is_kept_when_index_yml_was_kept(self):
        fs = self._fs(self.legacy)
        fs.write_text(INDEX, "name: own\n")
        assert init(InitConfig(target=PROJECT), fs) == 0
        assert fs.exists(self.old)
        assert fs.read_text(INDEX) == "name: own\n"

    def test_is_never_removed_when_its_the_projects_own(self, capsys: pytest.CaptureFixture[str]):
        own = "jobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: uv run pytest\n"
        fs = self._fs(own)
        assert init(InitConfig(target=PROJECT, force=True), fs) == 0
        assert fs.read_text(self.old) == own
        assert "Left .github/workflows/index.yml" in capsys.readouterr().out

    def test_is_left_with_a_warning_when_it_cant_be_read(self, capsys: pytest.CaptureFixture[str]):
        old = self.old

        class Unreadable(MemoryFileSystem):
            def read_text(self, path: Path) -> str:
                if path == old:
                    raise PermissionError(13, "Permission denied")
                return super().read_text(path)

        fs = Unreadable()
        fs.mkdir(old.parent, parents=True)
        fs.write_text(old, self.legacy)
        assert init(InitConfig(target=PROJECT), fs) == 0
        assert fs.exists(old)
        assert "Left .github/workflows/index.yml, which couldn't be read" in capsys.readouterr().out
