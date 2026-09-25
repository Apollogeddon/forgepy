from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOWS_DIR = Path(__file__).parent.parent / ".github" / "workflows"


def _workflow_files() -> list[Path]:
    return sorted(WORKFLOWS_DIR.glob("*.yml"))


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_workflow_yaml_parses(path: Path):
    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    assert isinstance(doc, dict)
    assert "jobs" in doc


def _local_workflow_refs(doc: dict) -> list[str]:
    refs = []
    for job in doc.get("jobs", {}).values():
        uses = job.get("uses") if isinstance(job, dict) else None
        if isinstance(uses, str) and uses.startswith("./.github/workflows/"):
            refs.append(uses.removeprefix("./"))
    return refs


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_local_workflow_references_exist(path: Path):
    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    repo_root = WORKFLOWS_DIR.parent.parent
    for ref in _local_workflow_refs(doc):
        assert (repo_root / ref).exists(), (
            f"{path.name} references missing workflow {ref}"
        )


def _declared_inputs(doc: dict) -> set[str]:
    on_block = doc.get(True, doc.get("on", {}))
    workflow_call = (
        on_block.get("workflow_call", {}) if isinstance(on_block, dict) else {}
    )
    return set((workflow_call or {}).get("inputs", {}).keys())


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_with_inputs_are_declared_by_callee(path: Path):
    with path.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    repo_root = WORKFLOWS_DIR.parent.parent
    for job in doc.get("jobs", {}).values():
        if not isinstance(job, dict):
            continue
        uses = job.get("uses")
        with_block = job.get("with")
        if not (
            isinstance(uses, str)
            and uses.startswith("./.github/workflows/")
            and with_block
        ):
            continue

        callee_path = repo_root / uses.removeprefix("./")
        with callee_path.open(encoding="utf-8") as f:
            callee_doc = yaml.safe_load(f)
        declared = _declared_inputs(callee_doc)
        for key in with_block:
            assert key in declared, (
                f"{path.name} passes undeclared input '{key}' to {uses}"
            )


def test_generated_index_yml_references_exist():
    """The CLI's generated index.yml points at apollogeddon/forgepy@main workflows.

    We can't fetch @main here, but we can confirm the referenced filenames exist
    in this very repo (i.e. what @main will actually serve).
    """
    from forgepy.templates import workflows as workflow_templates

    for template in (
        workflow_templates.LIBRARY_WORKFLOW,
        workflow_templates.SERVICE_WORKFLOW,
        workflow_templates.WEBSITE_WORKFLOW,
        workflow_templates.DEBIAN_WORKFLOW,
    ):
        rendered = workflow_templates.render(template, python_version="3.13")
        doc = yaml.safe_load(rendered)
        for job in doc["jobs"].values():
            uses = job["uses"]
            assert uses.startswith("apollogeddon/forgepy/.github/workflows/")
            filename = uses.split("/")[-1].split("@")[0]
            assert (WORKFLOWS_DIR / filename).exists(), (
                f"generated workflow references missing {filename}"
            )
