from __future__ import annotations

import re
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

from forgepy.config import DEFAULT_PYTHON_VERSION
from forgepy.templates import workflows as workflow_templates

WORKFLOWS_DIR = Path(__file__).parent.parent / ".github" / "workflows"
# PyYAML can produce non-str keys (YAML 1.1 parses a bare `on:` mapping key as
# the bool True), so keys are Any here rather than str.
YamlDoc = dict[Any, Any]


def _workflow_files() -> list[Path]:
    return sorted(WORKFLOWS_DIR.glob("*.yml"))


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_yaml_parses(path: Path):
    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    assert isinstance(doc, dict)
    assert "jobs" in doc


def _local_workflow_refs(doc: YamlDoc) -> list[str]:
    refs: list[str] = []
    jobs: YamlDoc = doc.get("jobs") or {}
    for raw_job in jobs.values():
        if not isinstance(raw_job, dict):
            continue
        job = cast(YamlDoc, raw_job)
        uses = job.get("uses")
        if isinstance(uses, str) and uses.startswith("./.github/workflows/"):
            refs.append(uses.removeprefix("./"))
    return refs


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_local_workflow_references_exist(path: Path):
    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    repo_root = WORKFLOWS_DIR.parent.parent
    for ref in _local_workflow_refs(doc):
        assert (repo_root / ref).exists(), f"{path.name} references missing workflow {ref}"


def _declared_inputs(doc: YamlDoc) -> set[str]:
    on_block: YamlDoc = doc.get(True) or doc.get("on") or {}
    workflow_call: YamlDoc = on_block.get("workflow_call") or {}
    inputs: YamlDoc = workflow_call.get("inputs") or {}
    return set(inputs.keys())


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_with_inputs_are_declared_by_callee(path: Path):
    with path.open(encoding="utf-8") as f:
        doc: YamlDoc = yaml.safe_load(f)

    repo_root = WORKFLOWS_DIR.parent.parent
    jobs: YamlDoc = doc.get("jobs") or {}
    for raw_job in jobs.values():
        if not isinstance(raw_job, dict):
            continue
        job = cast(YamlDoc, raw_job)
        uses = job.get("uses")
        with_block: YamlDoc = job.get("with") or {}
        if not (isinstance(uses, str) and uses.startswith("./.github/workflows/") and with_block):
            continue

        callee_path = repo_root / uses.removeprefix("./")
        with callee_path.open(encoding="utf-8") as f:
            callee_doc: YamlDoc = yaml.safe_load(f)
        declared = _declared_inputs(callee_doc)
        for key in with_block:
            assert key in declared, f"{path.name} passes undeclared input '{key}' to {uses}"


def test_generated_index_yml_references_exist():
    """Generated workflows reference apollogeddon/forgepy@main; this repo is what @main serves."""
    for template in (
        workflow_templates.LIBRARY_WORKFLOW,
        workflow_templates.SERVICE_WORKFLOW,
        workflow_templates.WEBSITE_WORKFLOW,
        workflow_templates.DEBIAN_WORKFLOW,
    ):
        docker = template is not workflow_templates.LIBRARY_WORKFLOW
        inputs = {"run_tests": False, "enable_versioning": False}
        rendered = workflow_templates.render(template, docker=docker, inputs=inputs)
        doc = yaml.safe_load(rendered)
        for job in doc["jobs"].values():
            uses = job.get("uses")
            if uses is None:
                continue
            assert uses.startswith("apollogeddon/forgepy/.github/workflows/")
            filename = uses.split("/")[-1].split("@")[0]
            assert (WORKFLOWS_DIR / filename).exists(), f"generated workflow references missing {filename}"
            with (WORKFLOWS_DIR / filename).open(encoding="utf-8") as f:
                declared = _declared_inputs(yaml.safe_load(f))
            with_block: YamlDoc = job.get("with") or {}
            for key in with_block:
                assert key in declared, f"generated workflow passes undeclared input '{key}' to {filename}"


@pytest.mark.parametrize("name", ["service.yml", "website.yml", "debian.yml"])
def test_pipelines_expose_release_outputs_for_docker_job(name: str):
    """The generated docker job reads the pipeline's version outputs to decide when to push."""
    with (WORKFLOWS_DIR / name).open(encoding="utf-8") as f:
        doc: YamlDoc = yaml.safe_load(f)
    on_block: YamlDoc = doc.get(True) or doc.get("on") or {}
    workflow_call: YamlDoc = on_block.get("workflow_call") or {}
    outputs: YamlDoc = workflow_call.get("outputs") or {}
    assert {"new_release_published", "version"} <= set(outputs)


def _version_job() -> YamlDoc:
    with (WORKFLOWS_DIR / "version.yml").open(encoding="utf-8") as f:
        doc: YamlDoc = yaml.safe_load(f)
    return doc["jobs"]["release-please"]


def test_version_reads_the_working_directory_release_config():
    """A project in a sub-directory keeps its release-please config in its own .github/."""
    release = next(s for s in _version_job()["steps"] if s.get("uses", "").startswith("googleapis/release-please"))
    for key, file in (("config-file", "release.json"), ("manifest-file", ".release.json")):
        assert f"format('{{0}}/.github/{file}', inputs.working_directory)" in release["with"][key]


@pytest.mark.parametrize("key", ["release_created", "version", "tag_name"])
def test_version_reads_the_working_directory_package_outputs(key: str):
    """release-please prefixes a sub-directory package's outputs with its path."""
    assert f"format('{{0}}--{key}', inputs.working_directory)" in _version_job()["outputs"][key]


def test_version_counts_any_package_release_only_for_the_root_package():
    """releases_created is true when any package is released, not just this one."""
    workflow = yaml.safe_load((WORKFLOWS_DIR / "version.yml").read_text(encoding="utf-8"))
    published = workflow[True]["workflow_call"]["outputs"]["new_release_published"]["value"]
    before_root_clause, root_clause = published.split("inputs.working_directory == '.' && ", 1)
    assert "releases_created" not in before_root_clause
    assert root_clause.startswith("(jobs.release-please.outputs.releases_created")


def test_generated_jython_workflow_inputs_are_declared():
    rendered = workflow_templates.render(workflow_templates.SERVICE_WORKFLOW, inputs={"run_build": False})
    job = yaml.safe_load(rendered)["jobs"]["service"]
    with (WORKFLOWS_DIR / "service.yml").open(encoding="utf-8") as f:
        declared = _declared_inputs(yaml.safe_load(f))
    assert set(job["with"]) <= declared


def _jobs(name: str) -> YamlDoc:
    return yaml.safe_load((WORKFLOWS_DIR / name).read_text(encoding="utf-8"))["jobs"]


@pytest.mark.parametrize("name", ["library.yml", "service.yml", "website.yml", "debian.yml"])
def test_dependabot_pull_requests_request_a_review(name: str):
    """CODEOWNERS requests nothing in a private repo on a free plan, so each pipeline asks itself, before the checks."""
    jobs = _jobs(name)
    review = jobs["review"]
    assert review["uses"] == "./.github/workflows/review.yml"
    assert "needs" not in review
    assert "github.event.pull_request.user.login == 'dependabot[bot]'" in review["if"]
    assert review["with"]["reviewers"] == "${{ inputs.reviewers }}"
    assert jobs["version"]["with"]["reviewers"] == "${{ inputs.reviewers }}"


def test_release_pull_request_requests_a_review():
    review = _jobs("version.yml")["review"]
    assert review["needs"] == ["release-please"]
    assert review["with"]["pull_request"] == "${{ needs.release-please.outputs.pr_number }}"


def test_review_request_never_fails_the_pipeline():
    script = (WORKFLOWS_DIR / "review.yml").read_text(encoding="utf-8")
    assert "catch (error)" in script
    assert "core.warning" in script


_SETUP_PYTHON = re.compile(r"uses: actions/setup-python@\S+\n\s+with:\n\s+python-version: (.+)")


@pytest.mark.parametrize(
    "path",
    [p for p in _workflow_files() if "uses: actions/setup-python" in p.read_text(encoding="utf-8")],
    ids=lambda p: p.name,
)
def test_setup_python_uses_the_resolved_version(path: Path):
    """The input wins, then the project's .python-version, then forgepy's default, which must match what init pins."""
    content = path.read_text(encoding="utf-8")
    setups = _SETUP_PYTHON.findall(content)
    assert setups
    assert all(version == "${{ steps.python.outputs.version }}" for version in setups)
    assert re.findall(r"else version=(\S+)", content) == [DEFAULT_PYTHON_VERSION] * len(setups)
    assert "elif [ -f .python-version ]" in content


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_python_version_input_defaults_to_empty(path: Path):
    doc: YamlDoc = yaml.safe_load(path.read_text(encoding="utf-8"))
    on_block: YamlDoc = doc.get(True) or doc.get("on") or {}
    workflow_call: YamlDoc = on_block.get("workflow_call") or {}
    inputs: YamlDoc = workflow_call.get("inputs") or {}
    if "python_version" in inputs:
        assert inputs["python_version"]["default"] == ""


def test_generated_workflow_leaves_the_version_to_python_version_file():
    for template in (workflow_templates.SERVICE_WORKFLOW, workflow_templates.LIBRARY_WORKFLOW):
        assert "python_version" not in workflow_templates.render(template)
