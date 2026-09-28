from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

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
        rendered = workflow_templates.render(template, python_version="3.13", docker=docker, inputs=inputs)
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
