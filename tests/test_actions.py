from __future__ import annotations

import dataclasses
import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from forgepy.config import DEBIAN_IMAGE, DEBIAN_PYTHON_VERSION, DEFAULT_PYTHON_VERSION, InitConfig
from forgepy.core import init
from forgepy.templates import legacy as legacy_templates
from forgepy.templates import workflows as workflow_templates
from forgepy.utils.filesystem import MemoryFileSystem

WORKFLOWS_DIR = Path(__file__).parent.parent / ".github" / "workflows"
FIXTURES = Path(__file__).parent / "fixtures" / "legacy"
# PyYAML can produce non-str keys (YAML 1.1 parses a bare `on:` mapping key as
# the bool True), so keys are Any here rather than str.
YamlDoc = dict[Any, Any]

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js to run the github-script body")

FILES = sorted(path.name for path in WORKFLOWS_DIR.iterdir() if path.suffix == ".yml")
ROOTS = [name for name in FILES if name.startswith(".")]
PIPELINES = [name for name in FILES if not name.startswith(".")]

# The spec's stages: a run page reads <pipeline> / <stage>, the same words in every forge
STAGES: dict[str, list[str]] = {
    "library": ["lint", "scan", "test", "build"],
    "service": ["lint", "scan", "test", "test (windows)", "test (macos)", "test (databases)", "build"],
    "website": ["lint", "scan", "test", "build", "check", "check (lighthouse)"],
    "debian": ["build", "test"],
    "docker": ["build", "test", "push"],
    "version": ["release"],
    "publish": ["package", "assets", "attest"],
    # check: a check of the deployed site, which forgepy doesn't run yet
    "pages": ["deploy", "check"],
    "patch": ["update"],
    "merge": ["review", "squash"],
}


def _load_text(text: str) -> YamlDoc:
    return cast(YamlDoc, yaml.safe_load(text))


def _load(name: str) -> YamlDoc:
    return _load_text((WORKFLOWS_DIR / name).read_text(encoding="utf-8"))


def _on(doc: YamlDoc) -> YamlDoc:
    return cast(YamlDoc, doc.get(True) or doc.get("on") or {})


def _workflow_call(name: str) -> YamlDoc:
    return cast(YamlDoc, _on(_load(name)).get("workflow_call") or {})


def _jobs(name: str) -> YamlDoc:
    return cast(YamlDoc, _load(name)["jobs"])


def _steps(name: str, job: str) -> list[YamlDoc]:
    return cast(list[YamlDoc], _jobs(name)[job]["steps"])


def _step(name: str, job: str, step: str) -> YamlDoc:
    return next(s for s in _steps(name, job) if s.get("name") == step)


def _in_vocabulary(pipeline: str, name: str) -> bool:
    """A stage, or a stage with a variant in brackets."""
    stages = STAGES.get(pipeline, [])
    return name in stages or re.sub(r" \([^)]+\)$", "", name) in stages


def _kebab(name: str) -> str:
    return re.sub(r"\s+", "-", re.sub(r"[()]", "", name).strip())


MODES: list[tuple[str, workflow_templates.IndexWorkflowOptions]] = []
for _mode, _debian, _docker, _versioning, _testing, _build in itertools.product(
    ("library", "service", "website"), (False, True), (False, True), (True, False), (True, False), (True, False)
):
    # --debian and --jython are backend-only, and a library has no Docker image
    if (_debian or not _build) and _mode != "service":
        continue
    if _docker and _mode == "library":
        continue
    _id = (
        f"{_mode}{' debian' if _debian else ''}{' docker' if _docker else ''}"
        f"{'' if _versioning else ' no-versioning'}{'' if _testing else ' no-testing'}{'' if _build else ' jython'}"
    )
    MODES.append(
        (
            _id,
            workflow_templates.IndexWorkflowOptions(
                mode=_mode, debian=_debian, docker=_docker, versioning=_versioning, testing=_testing, build=_build
            ),
        )
    )
GENERATED = [(name, workflow_templates.index_workflow(cfg)) for name, cfg in MODES]


# --- the workflow files ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", FILES)
def test_workflow_yaml_parses(name: str):
    doc = _load(name)
    assert isinstance(doc, dict)
    assert "jobs" in doc


def test_has_the_forge_pipelines_forgepy_needs_and_one_root_workflow():
    assert ROOTS == [".index.yml"]
    assert _load(".index.yml")["name"] == "index"
    assert {name.removesuffix(".yml") for name in PIPELINES} == set(STAGES)


@pytest.mark.parametrize("name", PIPELINES)
def test_pipeline_is_only_ever_called(name: str):
    doc = _load(name)
    assert list(_on(doc)) == ["workflow_call"]
    assert doc["name"] == name.removesuffix(".yml")


# a pipeline calling another would add a third level to the run page's names
@pytest.mark.parametrize("name", PIPELINES)
def test_pipeline_calls_no_other_pipeline(name: str):
    for job_id, job in _jobs(name).items():
        assert "uses" not in job, f"{name}:{job_id}"


@pytest.mark.parametrize("name", PIPELINES)
def test_pipeline_names_every_job_with_a_stage_from_the_spec(name: str):
    pipeline = name.removesuffix(".yml")
    for job_id, job in _jobs(name).items():
        assert "name" in job, f"{name}:{job_id} has no name"
        assert _in_vocabulary(pipeline, job["name"]), f"{name}:{job_id} is named {job['name']!r}"
        # the job id is the stage in kebab case
        assert job_id == _kebab(job["name"])


@pytest.mark.parametrize("name", FILES)
def test_names_every_step(name: str):
    for job_id, job in _jobs(name).items():
        for step in job.get("steps", []):
            assert step.get("name"), f"{name}:{job_id} has an unnamed step"


@pytest.mark.parametrize("name", PIPELINES)
def test_pipeline_jobs_ask_for_their_own_permissions(name: str):
    """A job that asks for none takes its caller's grant, which only publish's assets and attest do on purpose."""
    for job_id, job in _jobs(name).items():
        if (name, job_id) in {("publish.yml", "assets"), ("publish.yml", "attest")}:
            assert "permissions" not in job
        else:
            assert "permissions" in job, f"{name}:{job_id}"


@pytest.mark.skipif(shutil.which("actionlint") is None, reason="needs actionlint")
def test_workflows_and_every_generated_index_pass_actionlint(tmp_path: Path):
    # actionlint reads workflows from a .github/workflows directory
    generated = tmp_path / ".github" / "workflows"
    generated.mkdir(parents=True)
    for index, (_, text) in enumerate(GENERATED):
        (generated / f"index-{index}.yml").write_text(text, encoding="utf-8")
    files = [str(WORKFLOWS_DIR / name) for name in FILES] + sorted(str(path) for path in generated.iterdir())
    result = subprocess.run(["actionlint", *files], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stdout + result.stderr


# --- wiring: a caller's inputs, secrets, outputs and permissions match what it calls -------------

_LEVELS = {"none": 0, "read": 1, "write": 2}


def _expect_wiring(caller: str, doc: YamlDoc, resolve: Callable[[str], str | None]) -> None:
    for job_id, job in doc["jobs"].items():
        if "uses" not in job:
            assert job_id in ("changes", "scorecard"), f"{caller}:{job_id} runs steps itself"
            continue
        callee = resolve(job["uses"])
        assert callee is not None, f"{caller}:{job_id} calls {job['uses']}"
        assert (WORKFLOWS_DIR / callee).exists(), f"{caller}:{job_id} calls missing {callee}"
        pipeline = callee.removesuffix(".yml")
        # the root job's id is the pipeline's name, and a variant, or a matrix leg, names itself in brackets
        if job_id != pipeline or "name" in job:
            assert re.fullmatch(rf"{pipeline} \([^)]+\)", job.get("name", "")), f"{caller}:{job_id}"
        call = _workflow_call(callee)
        declared: YamlDoc = call.get("inputs") or {}
        passed: YamlDoc = job.get("with") or {}
        for key in passed:
            assert key in declared, f"{caller}:{job_id} passes undeclared input {key!r} to {callee}"
        for key, spec in declared.items():
            if spec.get("required"):
                assert key in passed, f"{caller}:{job_id} misses required {key}"
        # secrets go by name, never inherit, which hands every repository secret to a workflow elsewhere
        secrets: YamlDoc | str = job.get("secrets") or {}
        assert isinstance(secrets, dict), f"{caller}:{job_id} inherits secrets"
        for key in secrets:
            assert key in (call.get("secrets") or {}), f"{caller}:{job_id} passes undeclared secret {key!r}"
        # GitHub refuses the whole run when a called job asks for more than its caller grants
        grant: YamlDoc = job.get("permissions") or {}
        for called_id, called in _jobs(callee).items():
            asked: dict[str, str] = called.get("permissions") or {}
            for scope, level in asked.items():
                granted = _LEVELS[grant.get(scope, "none")]
                assert granted >= _LEVELS[level], f"{caller}:{job_id} grants {callee}:{called_id} too little {scope}"
    # every pipeline output a job reads is one its pipeline declares
    for needed, output in re.findall(r"needs\.([\w-]+)\.outputs\.(\w+)", yaml.safe_dump(doc)):
        uses = doc["jobs"].get(needed, {}).get("uses")
        callee = resolve(uses) if uses else None
        if callee:
            assert output in (_workflow_call(callee).get("outputs") or {}), f"{caller} reads {needed}.{output}"


def _local(uses: str) -> str | None:
    return uses.removeprefix("./.github/workflows/") if uses.startswith("./.github/workflows/") else None


def _at_main(uses: str) -> str | None:
    match = re.fullmatch(r"apollogeddon/forgepy/\.github/workflows/([\w-]+\.yml)@main", uses)
    return match.group(1) if match else None


def _dispatch_step() -> YamlDoc:
    scripted = (step for step in _steps("merge.yml", "squash") if "script" in step.get("with", {}))
    return next(step for step in scripted if "createDispatchEvent" in step["with"]["script"])


def _merge_dispatch_type() -> str:
    return cast(str, _dispatch_step()["env"]["DISPATCH_TYPE"])


_CONCURRENCY = {"group": "${{ github.workflow }}-${{ github.head_ref || github.run_id }}", "cancel-in-progress": True}
_PATCH_EVENTS = (
    "github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'"
    " || github.event_name == 'repository_dispatch'"
)


# --- forgepy's own .index.yml ----------------------------------------------------------------------


class TestOwnIndex:
    doc = _load(".index.yml")

    def test_calls_only_local_pipelines_with_inputs_they_declare_and_the_permissions_they_need(self):
        _expect_wiring(".index.yml", self.doc, _local)

    def test_keeps_its_change_detection_as_a_root_job(self):
        changes = self.doc["jobs"]["changes"]
        assert changes["name"] == "changes"
        assert changes["outputs"] == {
            "code": "${{ steps.diff.outputs.code }}",
            "docs": "${{ steps.diff.outputs.docs }}",
        }

    def test_checks_the_tool_as_a_library_and_the_docs_as_a_website(self):
        jobs = self.doc["jobs"]
        assert jobs["library"]["uses"] == "./.github/workflows/library.yml"
        assert jobs["website"]["uses"] == "./.github/workflows/website.yml"
        assert jobs["website"]["with"]["working_directory"] == "docs"
        assert jobs["pages"]["with"]["artifact_name"] == jobs["website"]["with"]["artifact_name"]
        # forgepy isn't on PyPI
        assert "publish" not in jobs

    def test_has_the_same_concurrency_as_a_generated_index(self):
        assert self.doc["concurrency"] == _load_text(GENERATED[0][1])["concurrency"] == _CONCURRENCY

    def test_refreshes_the_docs_sites_forgepy_files_on_the_schedule_a_manual_run_and_a_merge(self):
        jobs = self.doc["jobs"]
        # the tool has no .forgepy/ of its own
        assert "patch" not in jobs
        assert jobs["patch-docs"]["if"] == _PATCH_EVENTS
        assert jobs["patch-docs"]["with"]["working_directory"] == "docs"
        assert {"schedule", "workflow_dispatch", "repository_dispatch"} <= set(_on(self.doc))

    def test_listens_for_the_merge_pipelines_dispatch(self):
        assert _on(self.doc)["repository_dispatch"]["types"] == [_merge_dispatch_type()]

    def test_scores_itself_with_scorecard_on_main_and_weekly_only_when_public(self):
        scorecard = self.doc["jobs"]["scorecard"]
        assert scorecard["if"].startswith("github.event.repository.private == false && ")
        assert "github.event_name == 'push' || github.event_name == 'schedule'" in scorecard["if"]
        assert scorecard["permissions"] == {"contents": "read", "security-events": "write", "actions": "read"}
        score = next(step for step in scorecard["steps"] if "ossf/scorecard-action@" in step.get("uses", ""))
        assert score["with"]["publish_results"] is False
        upload = next(step for step in scorecard["steps"] if "codeql-action/upload-sarif@" in step.get("uses", ""))
        assert upload["with"]["sarif_file"] == score["with"]["results_file"]
        assert "schedule" in _on(self.doc)

    def test_merges_dependabot_pull_requests_only_after_every_check(self):
        merge = self.doc["jobs"]["merge"]
        assert set(merge["needs"]) == {"changes", "library", "website"}
        assert "!contains(needs.*.result, 'failure')" in merge["with"]["checks_passed"]


# --- the generated .index.yml ---------------------------------------------------------------------


@pytest.mark.parametrize(("name", "text"), GENERATED, ids=[name for name, _ in GENERATED])
class TestGeneratedIndex:
    def test_calls_forgepys_pipelines_at_main_with_inputs_they_declare_and_the_permissions_they_need(
        self, name: str, text: str
    ):
        _expect_wiring(f"generated {name}", _load_text(text), _at_main)

    def test_listens_for_the_merge_pipelines_dispatch(self, name: str, text: str):  # noqa: ARG002
        assert _on(_load_text(text))["repository_dispatch"]["types"] == [_merge_dispatch_type()]

    # each run outside a pull request has a group of its own, so a queued run on main is never cancelled
    def test_cancels_only_a_pull_requests_older_run(self, name: str, text: str):  # noqa: ARG002
        assert _load_text(text)["concurrency"] == _CONCURRENCY

    def test_patches_on_the_weekly_schedule_a_manual_run_and_a_dependabot_merge(self, name: str, text: str):  # noqa: ARG002
        doc = _load_text(text)
        assert doc["jobs"]["patch"]["if"] == f"${{{{ {_PATCH_EVENTS} }}}}"
        assert {"schedule", "workflow_dispatch", "repository_dispatch"} <= set(_on(doc))

    # only PyPI Trusted Publishing and GitHub Pages need an OIDC token
    def test_asks_for_id_token_only_to_publish_or_deploy(self, name: str, text: str):  # noqa: ARG002
        for job_id, job in _load_text(text)["jobs"].items():
            if job_id not in ("publish", "pages"):
                assert "id-token" not in job["permissions"], job_id

    # the Python version lives in .python-version, which the pipelines read
    def test_leaves_the_python_version_to_the_python_version_file(self, name: str, text: str):  # noqa: ARG002
        assert "python_version" not in text


def _generated_jobs(**options: Any) -> YamlDoc:
    cfg = dataclasses.replace(workflow_templates.IndexWorkflowOptions(mode="service"), **options)
    return cast(YamlDoc, _load_text(workflow_templates.index_workflow(cfg))["jobs"])


@pytest.mark.parametrize(
    ("options", "jobs"),
    [
        ({"mode": "library"}, ["version", "library", "publish", "patch", "merge"]),
        ({"mode": "service"}, ["version", "service", "patch", "merge"]),
        ({"mode": "website"}, ["version", "website", "pages", "patch", "merge"]),
        ({"debian": True}, ["version", "service", "debian", "publish", "patch", "merge"]),
        ({"docker": True}, ["version", "service", "docker", "patch", "merge"]),
        ({"mode": "library", "versioning": False}, ["library", "patch", "merge"]),
        ({"mode": "website", "versioning": False}, ["website", "pages", "patch", "merge"]),
        ({"debian": True, "versioning": False}, ["service", "debian", "patch", "merge"]),
    ],
)
def test_generated_index_has_the_jobs_for_its_mode(options: YamlDoc, jobs: list[str]):
    assert list(_generated_jobs(**options)) == jobs


def test_generated_index_turns_off_the_stages_a_project_doesnt_have():
    assert _generated_jobs(testing=False)["service"]["with"] == {"run_tests": False}
    assert _generated_jobs(build=False)["service"]["with"] == {"run_build": False}
    assert "with" not in _generated_jobs()["service"]


def test_generated_index_checks_a_release_before_shipping_it_and_every_pull_request():
    jobs = _generated_jobs(mode="library")
    assert "needs.version.outputs.new_release_published == 'true'" in jobs["library"]["if"]
    assert "github.event_name == 'pull_request'" in jobs["library"]["if"]
    assert "needs.library.result == 'success'" in jobs["publish"]["if"]
    assert jobs["publish"]["permissions"] == {"contents": "read", "id-token": "write", "attestations": "write"}


_PUBLIC = "github.event.repository.private == false"


# a free plan has artifact attestations and GitHub Pages only in a public repository; a missing
# field, as on a scheduled run, reads as private, which always works
def test_generated_library_attests_its_release_only_from_a_public_repository():
    assert _generated_jobs(mode="library")["publish"]["with"] == {"attest": f"${{{{ {_PUBLIC} }}}}"}
    assert "attest" not in _generated_jobs(debian=True)["publish"]["with"]


@pytest.mark.parametrize("versioning", [True, False])
def test_generated_website_deploys_only_from_a_public_repository(*, versioning: bool):
    assert _generated_jobs(mode="website", versioning=versioning)["pages"]["if"].endswith(f" && {_PUBLIC} }}}}")


def test_own_pages_deploys_only_from_a_public_repository():
    assert _load(".index.yml")["jobs"]["pages"]["if"].endswith(f" && {_PUBLIC}")


def test_never_negates_the_private_flag():
    """!github.event.repository.private is true when the field is missing, which would turn on public-only steps."""
    texts = [(WORKFLOWS_DIR / name).read_text(encoding="utf-8") for name in FILES] + [text for _, text in GENERATED]
    for text in texts:
        assert "!github.event.repository.private" not in text


def test_generated_index_pushes_the_image_only_on_a_release():
    assert _generated_jobs(docker=True)["docker"]["with"]["push"] == (
        "${{ needs.version.outputs.new_release_published == 'true' }}"
    )
    assert "with" not in _generated_jobs(docker=True, versioning=False)["docker"]


def test_generated_index_attaches_the_deb_to_the_release():
    assert _generated_jobs(debian=True)["publish"]["with"] == {
        "package": False,
        "assets": "debian-package",
        "tag_name": "${{ needs.version.outputs.tag_name }}",
    }
    assert _workflow_call("debian.yml")["outputs"]["package_artifact"]["value"] == "debian-package"


def test_generated_index_deploys_every_change_to_main_when_the_site_isnt_versioned():
    assert _generated_jobs(mode="website", versioning=False)["pages"]["if"] == (
        "${{ github.ref == 'refs/heads/main' && github.event_name != 'pull_request'"
        " && github.event.repository.private == false }}"
    )


def test_generated_index_merges_a_dependabot_pull_request_only_when_every_check_passed():
    merge = _generated_jobs(debian=True, docker=True)["merge"]
    assert merge["needs"] == ["service", "debian", "docker"]
    assert merge["with"]["checks_passed"] == (
        "${{ !contains(needs.*.result, 'failure') && !contains(needs.*.result, 'cancelled') }}"
    )


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("uses: apollogeddon/forgepy/.github/workflows/library.yml@main", True),
        ("uses: Apollogeddon/forgepy/.github/workflows/service.yml@main", True),
        ("uses: someone/else/.github/workflows/ci.yml@v1", False),
        ("runs-on: ubuntu-latest", False),
    ],
)
def test_recognises_a_workflow_calling_forgepy(content: str, *, expected: bool):
    assert workflow_templates.calls_forgepy(content) is expected


# --- workflows an earlier forgepy generated --------------------------------------------------------


@pytest.mark.parametrize(
    "fixture", ["backend.yml", "library.yml", "website.yml", "debian.yml", "backend-docker.yml", "backend-v0.2.0.yml"]
)
def test_knows_the_index_yml_an_earlier_forgepy_wrote(fixture: str):
    content = (FIXTURES / fixture).read_text(encoding="utf-8")
    assert legacy_templates.is_legacy_workflow(".github/workflows/index.yml", content)


def test_legacy_ignores_line_endings_trailing_spaces_and_blank_lines():
    content = (FIXTURES / "library.yml").read_text(encoding="utf-8").replace("\n", "  \r\n\r\n")
    assert legacy_templates.is_legacy_workflow(".github/workflows/index.yml", content)


def test_legacy_doesnt_know_a_changed_one_or_one_under_another_name():
    content = (FIXTURES / "library.yml").read_text(encoding="utf-8")
    changed = content.replace("    with:\n", "    with:\n      runs_on: xerus\n")
    assert not legacy_templates.is_legacy_workflow(".github/workflows/index.yml", changed)
    assert not legacy_templates.is_legacy_workflow(".github/workflows/build.yml", content)


def test_legacy_doesnt_know_what_this_forgepy_generates():
    for _, text in GENERATED:
        assert not legacy_templates.is_legacy_workflow(".github/workflows/index.yml", text)


# --- the check pipelines --------------------------------------------------------------------------

CHECKS = ["library.yml", "service.yml", "website.yml"]


@pytest.mark.parametrize("name", CHECKS)
def test_check_pipelines_share_their_lint_scan_test_and_build_stages(name: str):
    jobs = _jobs(name)
    assert [jobs[stage]["name"] for stage in ("lint", "scan", "test", "build")] == ["lint", "scan", "test", "build"]
    assert jobs["test"]["needs"] == ["lint", "scan"]
    # only needs the lint and scan to pass, so it runs alongside the tests
    assert jobs["build"]["needs"] == ["lint", "scan"]
    assert jobs["test"]["if"] == "inputs.run_tests"


# what ignition-demo and the other consumers pass, including a matrix of API groups through sync_args
@pytest.mark.parametrize("name", CHECKS)
@pytest.mark.parametrize(
    "key",
    [
        "runs_on",
        "working_directory",
        "python_version",
        "enable_secrets",
        "run_tests",
        "sync_args",
        "build_command",
        "artifact_name",
        "ref",
        "pre_build_command",
    ],
)
def test_check_pipelines_keep_the_inputs_consumers_pass(name: str, key: str):
    assert key in _workflow_call(name)["inputs"]


@pytest.mark.parametrize("name", ["library.yml", "service.yml"])
def test_check_pipelines_skip_the_build_with_run_build_false(name: str):
    assert _workflow_call(name)["inputs"]["run_build"]["default"] is True
    assert _jobs(name)["build"]["if"] == "inputs.run_build"


# a matrix caller's legs each name their artifacts, so two legs never upload under one name
@pytest.mark.parametrize("name", CHECKS)
def test_check_pipelines_name_their_uploads_after_the_artifact(name: str):
    assert _step(name, "test", "Upload coverage")["with"]["name"] == "coverage-${{ inputs.artifact_name }}"
    assert _step(name, "build", "Upload the build")["with"]["name"] == "${{ inputs.artifact_name }}"


def test_a_matrix_of_api_groups_calls_the_library_pipeline_as_variants():
    """As ignition-demo checks its Jython scripts once per Ignition API, each leg named `library (<api>)`."""
    caller = _load_text("""
on: pull_request
jobs:
  library:
    name: library (${{ matrix.api }})
    strategy:
      matrix:
        include:
          - { api: "8.1", group: ignition81 }
          - { api: "8.3", group: ignition83 }
    uses: apollogeddon/forgepy/.github/workflows/library.yml@main
    with:
      working_directory: projects
      sync_args: --no-default-groups --group dev --group ${{ matrix.group }}
      run_build: false
      artifact_name: projects-${{ matrix.group }}
    permissions:
      contents: read
      pull-requests: write
""")
    job = caller["jobs"]["library"]
    job["name"] = re.sub(r"\$\{\{ matrix\.api \}\}", "8.1", job["name"])
    _expect_wiring("matrix caller", caller, _at_main)


@pytest.mark.parametrize("name", CHECKS)
def test_lint_stage_runs_ruff_basedpyright_and_forgepys_checks(name: str):
    runs = [step.get("run", "") for step in _steps(name, "lint")]
    for command in (
        "uv run ruff check .",
        "uv run ruff format --check .",
        "uv run basedpyright",
        "uv run poe compat",
        "uv run forgepy sync --check",
    ):
        assert command in runs
    assert _step(name, "lint", "Check Jython 2.7 compatibility")["if"].startswith("hashFiles(")


@pytest.mark.parametrize("name", CHECKS)
def test_test_stage_runs_pytest_with_coverage(name: str):
    assert _step(name, "test", "Test")["run"] == "uv run pytest"
    upload = _step(name, "test", "Upload coverage")
    assert upload["if"] == "always()"
    assert "htmlcov" in upload["with"]["path"]


@pytest.mark.parametrize(("name", "default"), [("library.yml", "uv build"), ("website.yml", "uv run zensical build")])
def test_build_stage_runs_the_build_command_through_the_environment(name: str, default: str):
    assert _workflow_call(name)["inputs"]["build_command"]["default"] == default
    build = _step(name, "build", "Build")
    assert "${{" not in build["run"]
    assert build["env"] == {"BUILD_COMMAND": "${{ inputs.build_command }}"}


@pytest.mark.parametrize(("name", "job"), [(name, job) for name in CHECKS for job in ("lint", "scan", "test", "build")])
def test_jobs_check_out_the_ref(name: str, job: str):
    assert _step(name, job, "Check out")["with"]["ref"] == "${{ inputs.ref }}"


@pytest.mark.parametrize(("name", "job"), [(name, job) for name in CHECKS for job in ("lint", "test", "build")])
def test_pre_build_command_runs_before_installing(name: str, job: str):
    names = [step.get("name") for step in _steps(name, job)]
    assert names.index("Run the pre-build command") < names.index("Install dependencies")
    hook = _step(name, job, "Run the pre-build command")
    assert hook["if"] == "inputs.pre_build_command != ''"
    # through the environment, never interpolated into the script
    assert "${{" not in hook["run"]
    assert hook["env"] == {
        "GH_TOKEN": "${{ secrets.GH_TOKEN }}",
        "PRE_BUILD_COMMAND": "${{ inputs.pre_build_command }}",
    }
    assert _workflow_call(name)["secrets"]["GH_TOKEN"]["required"] is False


_SETUP_PYTHON = re.compile(r"uses: actions/setup-python@\S+\n\s+with:\n\s+python-version: (.+)")


@pytest.mark.parametrize(
    "name", [name for name in FILES if "uses: actions/setup-python" in (WORKFLOWS_DIR / name).read_text("utf-8")]
)
def test_setup_python_uses_the_resolved_version(name: str):
    """The input wins, then the project's .python-version, then forgepy's default, which must match what init pins."""
    content = (WORKFLOWS_DIR / name).read_text(encoding="utf-8")
    setups = _SETUP_PYTHON.findall(content)
    assert setups
    assert all(version == "${{ steps.python.outputs.version }}" for version in setups)
    assert re.findall(r"else version=(\S+)", content) == [DEFAULT_PYTHON_VERSION] * len(setups)
    assert "elif [ -f .python-version ]" in content


@pytest.mark.parametrize("name", PIPELINES)
def test_python_version_input_defaults_to_empty(name: str):
    inputs: YamlDoc = _workflow_call(name).get("inputs") or {}
    if "python_version" in inputs:
        assert inputs["python_version"]["default"] == ""


# --- website site checks --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "default"),
    [
        ("ref", ""),
        ("pre_build_command", ""),
        ("base_path", ""),
        ("check_links", False),
        ("check_external_links", False),
        ("link_check_args", ""),
        ("check_accessibility", False),
        ("accessibility_paths", ""),
        ("accessibility_impact", "serious"),
    ],
)
def test_website_inputs_default_to_what_callers_had(name: str, default: object):
    assert _workflow_call("website.yml")["inputs"][name]["default"] == default


def _site_step(name: str) -> YamlDoc:
    return _step("website.yml", "check", name)


def test_site_checks_are_opt_in_and_check_the_uploaded_build():
    check = _jobs("website.yml")["check"]
    assert check["if"] == "inputs.check_links || inputs.check_accessibility"
    assert check["needs"] == ["build"]
    assert _site_step("Download the build")["with"]["name"] == "${{ inputs.artifact_name }}"


def test_site_checks_only_check_what_is_asked():
    assert _site_step("Check links")["if"] == "inputs.check_links"
    for name in ("Install the accessibility checker", "Check accessibility"):
        # runs whatever the link check found
        assert "inputs.check_accessibility" in _site_step(name)["if"]
        assert "!cancelled()" in _site_step(name)["if"]


def test_link_check_is_internal_unless_asked():
    step = _site_step("Check links")
    assert re.fullmatch(r"lycheeverse/lychee-action@v\d+", step["uses"])
    assert "${{ !inputs.check_external_links && '--offline' || '' }}" in step["with"]["args"]
    assert "--root-dir '${{ steps.site.outputs.root }}'" in step["with"]["args"]
    assert step["with"]["fail"] is True


@pytest.mark.parametrize(
    ("base_path", "base"),
    [("", "/"), ("/", "/"), ("my-site", "/my-site/"), ("/my-site", "/my-site/"), ("/a/b/", "/a/b/")],
)
def test_site_is_staged_under_base_path(tmp_path: Path, base_path: str, base: str):
    build = tmp_path / "build"
    build.mkdir()
    (build / "index.html").write_text("<h1>hi</h1>", encoding="utf-8")
    (build / "sitemap.xml").write_text(
        "<urlset><url><loc>https://owner.github.io/my-site/</loc></url></urlset>", encoding="utf-8"
    )
    output = tmp_path / "output"
    env = {"PATH": os.environ["PATH"], "BASE_PATH": base_path, "BUILD": str(build)}
    env |= {"RUNNER_TEMP": str(tmp_path), "GITHUB_OUTPUT": str(output)}
    subprocess.run(["bash", "-e", "-c", _site_step("Stage the site for checking")["run"]], env=env, check=True)
    outputs = dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())
    root = tmp_path / "site"
    assert outputs["root"] == str(root)
    assert outputs["base"] == base
    assert (root / base.strip("/") / "index.html").is_file()
    # links to the site's own address are checked in the staged copy
    assert outputs["remap"] == rf"--remap '^https://owner\.github\.io/ file://{root}/'"


@pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js")
def test_accessibility_checker_parses(tmp_path: Path):
    run = _site_step("Install the accessibility checker")["run"]
    match = re.search(r"<<'EOF'\n(.*?)\nEOF", run, re.DOTALL)
    assert match
    script = tmp_path / "check.mjs"
    script.write_text(match.group(1), encoding="utf-8")
    assert "AxeBuilder" in match.group(1)
    subprocess.run(["node", "--check", str(script)], check=True)


# --- version, review requests and merge -----------------------------------------------------------


def _release_job() -> YamlDoc:
    return cast(YamlDoc, _jobs("version.yml")["release"])


def test_version_reads_the_working_directory_release_config():
    """A project in a sub-directory keeps its release-please config in its own .github/."""
    release = _step("version.yml", "release", "Release")
    for key, file in (("config-file", "release.json"), ("manifest-file", ".release.json")):
        assert f"format('{{0}}/.github/{file}', inputs.working_directory)" in release["with"][key]


@pytest.mark.parametrize("key", ["release_created", "version", "tag_name"])
def test_version_reads_the_working_directory_package_outputs(key: str):
    """release-please prefixes a sub-directory package's outputs with its path."""
    assert f"format('{{0}}--{key}', inputs.working_directory)" in _release_job()["outputs"][key]


def test_version_counts_any_package_release_only_for_the_root_package():
    """releases_created is true when any package is released, not just this one."""
    published = _workflow_call("version.yml")["outputs"]["new_release_published"]["value"]
    before_root_clause, root_clause = published.split("inputs.working_directory == '.' && ", 1)
    assert "releases_created" not in before_root_clause
    assert root_clause.startswith("(jobs.release.outputs.releases_created")


def test_release_please_runs_as_a_github_app_only_when_one_is_set():
    inputs = _workflow_call("version.yml")["inputs"]
    assert inputs["app_client_id"]["default"] == ""
    assert _workflow_call("version.yml")["secrets"]["APP_PRIVATE_KEY"]["required"] is False
    app = _step("version.yml", "release", "Create the app's token")
    assert app["if"] == "inputs.app_client_id != ''"
    assert app["with"] == {"client-id": "${{ inputs.app_client_id }}", "private-key": "${{ secrets.APP_PRIVATE_KEY }}"}
    release = _step("version.yml", "release", "Release")
    assert release["with"]["token"] == "${{ steps.app.outputs.token || secrets.GITHUB_TOKEN }}"  # noqa: S105


_APP_INPUTS = {"app_client_id": "${{ vars.RELEASE_APP_CLIENT_ID }}"}
_APP_SECRETS = {"APP_PRIVATE_KEY": "${{ secrets.RELEASE_APP_PRIVATE_KEY }}"}


@pytest.mark.parametrize(("name", "text"), [(".index.yml", None), *GENERATED[:1]], ids=["own", "generated"])
def test_version_jobs_pass_the_release_app_when_one_is_set(name: str, text: str | None):
    version = (_load(name) if text is None else _load_text(text))["jobs"]["version"]
    assert _APP_INPUTS.items() <= version["with"].items()
    assert version["secrets"] == _APP_SECRETS


# with GITHUB_TOKEN no checks start on a release pull request anyway; with an app's token they should run
@pytest.mark.parametrize("text", [(WORKFLOWS_DIR / ".index.yml").read_text("utf-8"), *(t for _, t in GENERATED)])
def test_checks_run_on_release_please_branches(text: str):
    assert "release-please--" not in text


def test_release_pull_request_requests_a_review():
    review = _step("version.yml", "release", "Request a review")
    assert review["if"] == "steps.release.outputs.pr != ''"
    assert review["env"]["REVIEWERS"] == "${{ inputs.reviewers }}"


def test_dependabot_pull_requests_request_a_review_whether_or_not_the_checks_passed():
    review = _jobs("merge.yml")["review"]
    assert "checks_passed" not in review["if"]
    assert "github.event.pull_request.user.login == 'dependabot[bot]'" in review["if"]


@pytest.mark.parametrize(("name", "job"), [("version.yml", "release"), ("merge.yml", "review")])
def test_review_request_never_fails_the_pipeline(name: str, job: str):
    script = _step(name, job, "Request a review")["with"]["script"]
    assert "catch (error)" in script
    assert "core.warning" in script


# the author alone would merge someone else's push to Dependabot's branch, and the actor alone
# a pull request someone else opened that Dependabot then updated
def test_squash_needs_the_checks_and_dependabot_to_open_the_pull_request_and_make_its_latest_change():
    gate = str(_jobs("merge.yml")["squash"]["if"])
    assert gate.startswith("inputs.checks_passed && ")
    assert "github.event.pull_request.user.login == 'dependabot[bot]' && " in gate
    assert "github.actor == 'dependabot[bot]' && " in gate
    assert "!startsWith(github.head_ref, 'dependabot/github_actions/')" in gate
    assert "||" not in gate
    assert _workflow_call("merge.yml")["inputs"]["checks_passed"]["default"] is False


def test_squash_merges_only_a_pull_request_from_this_repository():
    gate = str(_jobs("merge.yml")["squash"]["if"])
    assert "github.event.pull_request.head.repo.full_name == github.repository" in gate


def test_squash_reads_the_update_type_first_and_passes_it_through_the_environment():
    steps = _steps("merge.yml", "squash")
    assert steps[0]["id"] == "metadata"
    assert re.match(r"dependabot/fetch-metadata@", steps[0]["uses"])
    assert steps[0]["with"]["github-token"] == "${{ secrets.GITHUB_TOKEN }}"
    merge = _step("merge.yml", "squash", "Enable auto-merge")
    assert merge["env"]["UPDATE_TYPE"] == "${{ steps.metadata.outputs.update-type }}"
    assert "steps.metadata" not in merge["with"]["script"]


# runs the squash step's github-script body under Node, with GitHub's API answering as a branch with no
# protection rules does, so the step merges straight away
_SQUASH_HARNESS = """
const calls = { notice: [], info: [], warning: [], graphql: [], merge: [], dispatch: [] };
const record = (kind) => (message) => calls[kind].push(message);
const core = { notice: record('notice'), info: record('info'), warning: record('warning') };
const github = {
  graphql: async (query, vars) => { calls.graphql.push(vars); throw new Error('Pull request is in clean status'); },
  rest: {
    pulls: { merge: async (args) => { calls.merge.push(args); } },
    repos: { createDispatchEvent: async (args) => { calls.dispatch.push(args); } },
  },
};
const context = {
  repo: { owner: 'o', repo: 'r' },
  payload: { pull_request: { number: 7, node_id: 'PR_7', head: { sha: 'abc123' }, base: { ref: 'main' } } },
};
const body = require('node:fs').readFileSync(process.argv[1], 'utf8');
const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;
new AsyncFunction('require', 'core', 'github', 'context', body)(require, core, github, context)
  .then(() => console.log(JSON.stringify(calls)));
"""


def _run_squash(tmp_path: Path, update_type: str) -> dict[str, list[Any]]:
    step = _step("merge.yml", "squash", "Enable auto-merge")
    script = tmp_path / "squash.js"
    script.write_text(step["with"]["script"], encoding="utf-8")
    env = {**os.environ, "DISPATCH_TYPE": step["env"]["DISPATCH_TYPE"], "UPDATE_TYPE": update_type}
    node = cast(str, shutil.which("node"))
    harness = [node, "-e", _SQUASH_HARNESS, str(script)]
    out = subprocess.run(harness, env=env, capture_output=True, text=True, check=True)
    return cast(dict[str, list[Any]], json.loads(out.stdout))


@needs_node
@pytest.mark.parametrize("update_type", ["version-update:semver-minor", "version-update:semver-patch"])
def test_squash_merges_a_minor_or_patch_update_at_the_commit_the_checks_ran_on(tmp_path: Path, update_type: str):
    calls = _run_squash(tmp_path, update_type)
    assert calls["graphql"] == [{"id": "PR_7", "oid": "abc123"}]
    assert calls["merge"] == [{"owner": "o", "repo": "r", "pull_number": 7, "merge_method": "squash", "sha": "abc123"}]
    assert len(calls["dispatch"]) == 1
    assert calls["notice"] == []


@needs_node
@pytest.mark.parametrize("update_type", ["version-update:semver-major", ""])
def test_squash_leaves_a_major_or_unclassified_update_to_a_person(tmp_path: Path, update_type: str):
    calls = _run_squash(tmp_path, update_type)
    assert calls["graphql"] == calls["merge"] == calls["dispatch"] == []
    assert len(calls["notice"]) == 1


def test_squash_enables_auto_merge_only_for_the_checked_commit():
    script = _step("merge.yml", "squash", "Enable auto-merge")["with"]["script"]
    assert "expectedHeadOid: $oid" in script


def test_squash_sends_the_auto_merged_dispatch_once_it_merges():
    assert _merge_dispatch_type() == "auto-merged"
    assert "dispatchOnceMerged" in _dispatch_step()["with"]["script"]


# --- pages, publish and patch ---------------------------------------------------------------------


def test_pages_deploys_one_at_a_time_in_a_group_a_callers_concurrency_cant_share():
    deploy = _jobs("pages.yml")["deploy"]
    assert deploy["concurrency"] == {"group": "pages-deploy", "cancel-in-progress": False}
    assert deploy["permissions"] == {"pages": "write", "id-token": "write"}
    assert _step("pages.yml", "deploy", "Download the build")["with"]["name"] == "${{ inputs.artifact_name }}"


def test_publish_caps_the_package_stage_and_lets_assets_and_attest_take_the_callers_grant():
    jobs = _jobs("publish.yml")
    assert jobs["package"]["permissions"] == {"contents": "read", "id-token": "write"}
    assert "permissions" not in jobs["assets"]
    assert "permissions" not in jobs["attest"]


def test_publish_ships_the_tested_build_without_installing_anything():
    steps = _steps("publish.yml", "package")
    assert _step("publish.yml", "package", "Download the build")["with"]["name"] == "${{ inputs.artifact_name }}"
    assert _step("publish.yml", "package", "Set up uv")["with"]["enable-cache"] is False
    runs = "\n".join(step.get("run", "") for step in steps)
    assert "uv publish" in runs
    assert "uv sync" not in runs


def test_publish_attests_what_the_other_stages_shipped_only_when_asked():
    attest = _jobs("publish.yml")["attest"]
    assert "inputs.attest" in attest["if"]
    assert attest["needs"] == ["package", "assets"]
    assert _workflow_call("publish.yml")["inputs"]["attest"]["default"] is False


def test_publish_attaches_assets_only_when_given_an_artifact():
    assert _jobs("publish.yml")["assets"]["if"] == "inputs.assets != ''"
    script = _step("publish.yml", "assets", "Upload the assets to the release")["with"]["script"]
    assert "throw new Error('assets needs tag_name" in script


def test_patch_only_refreshes_forgepys_files_and_leaves_vulnerable_packages_to_dependabot():
    text = (WORKFLOWS_DIR / "patch.yml").read_text(encoding="utf-8")
    for gone in ("osv-scanner", "uv lock", "--upgrade-package", "git-auto-commit-action"):
        assert gone not in text
    assert _step("patch.yml", "update", "Refresh forgepy's files")["run"] == "uv run --locked forgepy sync"
    assert _jobs("patch.yml")["update"]["if"] == "github.ref == 'refs/heads/main'"
    assert _jobs("patch.yml")["update"]["permissions"] == {"contents": "write", "pull-requests": "write"}


def test_patch_gives_its_token_only_to_the_push():
    assert _step("patch.yml", "update", "Check out")["with"]["persist-credentials"] is False
    for step in _steps("patch.yml", "update"):
        if "secrets.GITHUB_TOKEN" in yaml.safe_dump(step):
            assert step["name"] == "Push the refresh"


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def _run_patch_push(tmp_path: Path, working_directory: str, *, change: bool) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    repo = tmp_path / "repo"
    project = repo / working_directory
    (project / ".forgepy").mkdir(parents=True)
    (project / ".forgepy" / "ruff.toml").write_text("old\n", encoding="utf-8")
    _git(tmp_path, "init", "-q", "-b", "main", str(repo))
    _git(repo, "add", ".")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "init")
    _git(repo, "remote", "add", "origin", str(remote))
    if change:
        (project / ".forgepy" / "ruff.toml").write_text("new\n", encoding="utf-8")
    step = _step("patch.yml", "update", "Push the refresh")
    output = tmp_path / "output"
    output.touch()
    branch = "forgepy/sync" if working_directory == "." else f"forgepy/sync-{working_directory}"
    env = {**os.environ, "GH_TOKEN": "token", "BRANCH": branch, "GITHUB_OUTPUT": str(output)}
    subprocess.run(["bash", "-e", "-c", step["run"]], cwd=project, env=env, check=True, capture_output=True)
    return remote, output


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
@pytest.mark.parametrize(("working_directory", "branch"), [(".", "forgepy/sync"), ("docs", "forgepy/sync-docs")])
def test_patch_pushes_a_refresh_to_its_own_branch_not_main(tmp_path: Path, working_directory: str, branch: str):
    remote, output = _run_patch_push(tmp_path, working_directory, change=True)
    assert _git(remote, "branch", "--format=%(refname:short)") == branch
    assert _git(remote, "log", "-1", "--format=%s", branch) == "chore(deps): refresh the files forgepy manages"
    assert output.read_text(encoding="utf-8") == f"branch={branch}\n"


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_patch_pushes_nothing_when_nothing_changed(tmp_path: Path):
    remote, output = _run_patch_push(tmp_path, ".", change=False)
    assert _git(remote, "branch") == ""
    assert output.read_text(encoding="utf-8") == ""
    assert _step("patch.yml", "update", "Propose the refresh")["if"] == "steps.push.outputs.branch != ''"


def test_patch_opens_a_pull_request_only_when_none_is_open():
    script = _step("patch.yml", "update", "Propose the refresh")["with"]["script"]
    assert script.index("pulls.list") < script.index("pulls.create")
    assert "chore(deps): refresh the files forgepy manages" in script


# --- debian and docker ----------------------------------------------------------------------------


def test_debian_build_runs_in_the_image_init_checks_python_against():
    assert _jobs("debian.yml")["build"]["container"] == DEBIAN_IMAGE


def _minor(version: str) -> tuple[int, int]:
    major, minor = version.split(".")[:2]
    return int(major), int(minor)


def test_debian_build_images_python_meets_a_default_debian_projects_requires_python():
    """The deb is built against the image's python3, so it must satisfy what init writes for a --debian project."""
    fs = MemoryFileSystem()
    project = Path("project")
    assert init(InitConfig(target=project, debian=True), fs) == 0
    requires = tomllib.loads(fs.read_text(project / "pyproject.toml"))["project"]["requires-python"]
    floor = re.fullmatch(r">=(\d+\.\d+)(?:\.\d+)?", requires)
    assert floor is not None
    assert _minor(floor.group(1)) <= _minor(DEBIAN_PYTHON_VERSION)
    assert _minor(fs.read_text(project / ".python-version").strip()) <= _minor(DEBIAN_PYTHON_VERSION)


def test_debian_build_installs_its_tools_pinned_and_verified():
    steps = _steps("debian.yml", "build")
    runs = "\n".join(str(step.get("run", "")) for step in steps)
    assert not re.search(r"\|\s*(ba)?sh\b", runs)
    assert "releases/latest" not in runs
    assert any(str(step.get("uses", "")).startswith("astral-sh/setup-uv@v") for step in steps)
    nfpm = _step("debian.yml", "build", "Install nfpm")
    assert re.fullmatch(r"\d+\.\d+\.\d+", nfpm["env"]["NFPM_VERSION"])
    assert re.fullmatch(r"[0-9a-f]{64}", nfpm["env"]["NFPM_SHA256"])


@pytest.mark.skipif(shutil.which("sha256sum") is None, reason="needs sha256sum")
def test_debian_build_refuses_an_nfpm_download_that_fails_its_checksum(tmp_path: Path):
    nfpm = _step("debian.yml", "build", "Install nfpm")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    installed = tmp_path / "installed"
    # curl writes a tampered package; apt-get records whether it was asked to install anything
    (bin_dir / "curl").write_text('#!/bin/sh\nwhile [ "$1" != "-o" ]; do shift; done\necho tampered > "$2"\n')
    (bin_dir / "apt-get").write_text(f'#!/bin/sh\ntouch "{installed}"\n')
    for tool in ("curl", "apt-get"):
        (bin_dir / tool).chmod(0o755)
    env = {
        **os.environ,
        **nfpm["env"],
        "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(tmp_path),
    }
    result = subprocess.run(["bash", "-e", "-c", nfpm["run"]], env=env, capture_output=True, check=False)
    assert result.returncode != 0
    assert not installed.exists()


def test_debian_test_stage_reads_back_the_built_package():
    test = _jobs("debian.yml")["test"]
    assert test["needs"] == ["build"]
    assert _step("debian.yml", "test", "Download the package")["with"]["name"] == "debian-package"
    assert "dpkg-deb --field" in _step("debian.yml", "test", "Test")["run"]


def test_docker_builds_arm64_natively_only_when_asked_and_pushes_only_when_asked():
    jobs = _jobs("docker.yml")
    assert jobs["build-arm64"]["runs-on"] == "ubuntu-24.04-arm"
    assert "inputs.native_arm" in jobs["build-arm64"]["if"]
    assert "inputs.push" in jobs["push"]["if"]
    assert jobs["push"]["needs"] == ["build", "build-arm64"]
    assert _workflow_call("docker.yml")["inputs"]["push"]["default"] is False


# --- the OSV gate ---------------------------------------------------------------------------------

# runs the report step's github-script body under Node with a stand-in for its core API
_OSV_HARNESS = """
const calls = { info: [], warning: [], error: [], setFailed: [] };
const record = (kind) => (message) => calls[kind].push(message);
const core = {
  info: record('info'), warning: record('warning'), error: record('error'), setFailed: record('setFailed'),
  summary: { addHeading() { return this; }, addTable() { return this; }, async write() {} },
};
const body = require('node:fs').readFileSync(process.argv[1], 'utf8');
const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;
new AsyncFunction('require', 'core', body)(require, core).then(() => console.log(JSON.stringify(calls)));
"""


def _run_osv_report(
    tmp_path: Path, status: int, results: list[YamlDoc] | None, *, enforce: bool
) -> dict[str, list[str]]:
    report = _step("library.yml", "scan", "Report OSV findings")
    script = tmp_path / "report.js"
    script.write_text(report["with"]["script"], encoding="utf-8")
    osv_json = tmp_path / "osv.json"
    if results is not None:
        osv_json.write_text(json.dumps({"results": results}), encoding="utf-8")
    env = {
        **os.environ,
        "OSV_STATUS": str(status),
        "OSV_REPORT": str(osv_json),
        "OSV_ENFORCE": "true" if enforce else "false",
        "GITHUB_WORKSPACE": str(tmp_path),
    }
    node = cast(str, shutil.which("node"))
    out = subprocess.run([node, "-e", _OSV_HARNESS, str(script)], env=env, capture_output=True, text=True, check=True)
    return cast(dict[str, list[str]], json.loads(out.stdout))


def _finding(advisory: str, max_severity: str, rating: str | None = None) -> YamlDoc:
    return {
        "package": {"name": f"pkg-{advisory}", "version": "1.0.0"},
        "vulnerabilities": [
            {"id": advisory, "summary": advisory, "database_specific": {"severity": rating} if rating else {}}
        ],
        "groups": [{"ids": [advisory], "max_severity": max_severity}],
    }


# a public repository's pull requests only: a private one needs GitHub Code Security for it
@pytest.mark.parametrize("name", CHECKS)
def test_scan_reviews_a_public_repositorys_pull_request_dependency_changes(name: str):
    review = _step(name, "scan", "Review the dependency changes")
    assert review["if"] == "github.event_name == 'pull_request' && github.event.repository.private == false"
    assert re.match(r"actions/dependency-review-action@", review["uses"])
    assert review["with"] == {"fail-on-severity": "high"}
    assert review == _step("library.yml", "scan", "Review the dependency changes")


@pytest.mark.parametrize("name", CHECKS)
def test_osv_scan_never_swallows_the_result_and_is_the_same_in_every_check_pipeline(name: str):
    scan = _step(name, "scan", "Scan with OSV")
    report = _step(name, "scan", "Report OSV findings")
    assert "|| true" not in scan["run"]
    assert '"$RUNNER_TEMP/osv-scanner/osv-scanner" scan' in scan["run"]
    names = [step.get("name") for step in _steps(name, "scan")]
    assert names.index("Install OSV-Scanner") == names.index("Scan with OSV") - 1
    assert report["env"]["OSV_ENFORCE"] == "${{ github.event_name == 'pull_request' }}"
    assert report == _step("library.yml", "scan", "Report OSV findings")


@needs_node
@pytest.mark.parametrize(("enforce", "failed"), [(True, 1), (False, 0)])
def test_osv_report_fails_only_a_pull_request_on_a_high_finding(tmp_path: Path, *, enforce: bool, failed: int):
    lockfile = {"source": {"path": str(tmp_path / "uv.lock")}}
    calls = _run_osv_report(
        tmp_path,
        1,
        [{**lockfile, "packages": [_finding("GHSA-high", "9.8"), _finding("GHSA-low", "5.3")]}],
        enforce=enforce,
    )
    assert len(calls["setFailed"]) == failed
    assert any("GHSA-high" in message for message in calls["error"])
    assert any("GHSA-low" in message for message in calls["warning"])


@needs_node
def test_osv_report_uses_the_advisory_rating_without_a_score(tmp_path: Path):
    lockfile = {"source": {"path": str(tmp_path / "uv.lock")}}
    calls = _run_osv_report(tmp_path, 1, [{**lockfile, "packages": [_finding("GHSA-c", "", "CRITICAL")]}], enforce=True)
    assert len(calls["setFailed"]) == 1


@needs_node
@pytest.mark.parametrize(("status", "results"), [(0, []), (128, [])])
def test_osv_report_passes_when_there_is_nothing_to_report(tmp_path: Path, status: int, results: list[YamlDoc]):
    calls = _run_osv_report(tmp_path, status, results, enforce=True)
    assert calls["setFailed"] == []
    assert calls["warning"] == []


# a pull request mustn't pass with its dependencies unchecked; elsewhere OSV's API being down mustn't stop a release
@needs_node
@pytest.mark.parametrize(("status", "results"), [(127, []), (1, None)])
@pytest.mark.parametrize("enforce", [True, False])
def test_osv_report_fails_only_a_pull_request_it_couldnt_scan(
    tmp_path: Path, status: int, results: list[YamlDoc] | None, *, enforce: bool
):
    calls = _run_osv_report(tmp_path, status, results, enforce=enforce)
    assert len(calls["setFailed"]) == (1 if enforce else 0)
    assert len(calls["warning"]) == (0 if enforce else 1)


_OSV_INSTALLS = [name for name in FILES if "- name: Install OSV-Scanner" in (WORKFLOWS_DIR / name).read_text("utf-8")]


def _osv_install(name: str) -> YamlDoc:
    job = next(job for job in _jobs(name) if any(s.get("name") == "Install OSV-Scanner" for s in _steps(name, job)))
    return _step(name, job, "Install OSV-Scanner")


def test_every_check_pipeline_installs_osv_scanner_the_same_way():
    assert set(CHECKS) <= set(_OSV_INSTALLS)
    for name in _OSV_INSTALLS:
        assert _osv_install(name) == _osv_install("library.yml"), name
        assert "releases/latest" not in (WORKFLOWS_DIR / name).read_text(encoding="utf-8")


def test_osv_scanner_is_a_pinned_release():
    assert re.fullmatch(r"v\d+\.\d+\.\d+", _osv_install("library.yml")["env"]["OSV_SCANNER_VERSION"])


def _install_osv_scanner(tmp_path: Path, binary: str, sums: str, arch: str = "X64") -> subprocess.CompletedProcess[str]:
    """Runs the install step with a curl that serves `binary` and the checksum file `sums`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    served = tmp_path / "served"
    served.mkdir()
    (served / "osv-scanner_linux_amd64").write_text(binary, encoding="utf-8")
    (served / "osv-scanner_SHA256SUMS").write_text(sums, encoding="utf-8")
    curl = bin_dir / "curl"
    curl.write_text(f'#!/bin/sh\nfor last; do :; done\ncp "{served}/${{last##*/}}" .\n', encoding="utf-8")
    curl.chmod(0o755)
    step = _osv_install("library.yml")
    env = {**os.environ, **step["env"], "ARCH": arch, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    env["RUNNER_TEMP"] = str(tmp_path)
    return subprocess.run(["bash", "-e", "-c", step["run"]], env=env, capture_output=True, text=True, check=False)


needs_sha256sum = pytest.mark.skipif(shutil.which("sha256sum") is None, reason="needs sha256sum")


@needs_sha256sum
def test_osv_scanner_installs_a_download_that_matches_its_checksum(tmp_path: Path):
    digest = hashlib.sha256(b"scanner").hexdigest()
    result = _install_osv_scanner(tmp_path, "scanner", f"{digest}  osv-scanner_linux_amd64\n{'0' * 64}  other\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert os.access(tmp_path / "osv-scanner" / "osv-scanner", os.X_OK)


@needs_sha256sum
def test_osv_scanner_refuses_a_download_that_fails_its_checksum(tmp_path: Path):
    digest = hashlib.sha256(b"scanner").hexdigest()
    result = _install_osv_scanner(tmp_path, "tampered", f"{digest}  osv-scanner_linux_amd64\n")
    assert result.returncode != 0
    assert not (tmp_path / "osv-scanner" / "osv-scanner").exists()


def test_osv_scanner_refuses_a_runner_it_has_no_build_for(tmp_path: Path):
    result = _install_osv_scanner(tmp_path, "scanner", "", arch="X86")
    assert result.returncode != 0
    assert "no Linux build for X86" in result.stdout
