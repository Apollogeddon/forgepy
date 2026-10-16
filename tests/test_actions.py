from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
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


def _workflow_call(name: str) -> YamlDoc:
    doc: YamlDoc = yaml.safe_load((WORKFLOWS_DIR / name).read_text(encoding="utf-8"))
    on_block: YamlDoc = doc.get(True) or doc.get("on") or {}
    return on_block.get("workflow_call") or {}


@pytest.mark.parametrize("path", _workflow_files(), ids=lambda p: p.name)
def test_passed_secrets_are_declared_by_callee(path: Path):
    for job in _jobs(path.name).values():
        uses = job.get("uses")
        secrets: YamlDoc = job.get("secrets") or {}
        if not (isinstance(uses, str) and uses.startswith("./.github/workflows/")):
            continue
        callee_secrets: YamlDoc = _workflow_call(uses.split("/")[-1]).get("secrets") or {}
        for key in secrets:
            assert key in callee_secrets, f"{path.name} passes undeclared secret '{key}' to {uses}"


# every new input keeps what a caller that doesn't set it already gets
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


@pytest.mark.parametrize("job", ["testing", "release-testing"])
def test_website_passes_the_build_options_to_testing(job: str):
    call = _jobs("website.yml")[job]
    for name in ("ref", "pre_build_command"):
        assert call["with"][name] == f"${{{{ inputs.{name} }}}}"
    assert call["secrets"] == {"GH_TOKEN": "${{ secrets.GH_TOKEN }}"}


def test_testing_passes_the_build_options_to_quality():
    call = _jobs("testing.yml")["quality"]
    for name in ("ref", "pre_build_command"):
        assert call["with"][name] == f"${{{{ inputs.{name} }}}}"
    assert call["secrets"] == {"GH_TOKEN": "${{ secrets.GH_TOKEN }}"}
    for name in ("website.yml", "testing.yml", "quality.yml"):
        assert _workflow_call(name)["secrets"]["GH_TOKEN"]["required"] is False


@pytest.mark.parametrize(
    ("name", "job"),
    [("quality.yml", "secure"), ("quality.yml", "linting"), ("testing.yml", "testing"), ("testing.yml", "build")],
)
def test_jobs_check_out_the_ref(name: str, job: str):
    steps = _jobs(name)[job]["steps"]
    checkout = next(step for step in steps if step.get("uses", "").startswith("actions/checkout"))
    assert checkout["with"]["ref"] == "${{ inputs.ref }}"


@pytest.mark.parametrize(
    ("name", "job"), [("quality.yml", "linting"), ("testing.yml", "testing"), ("testing.yml", "build")]
)
def test_pre_build_command_runs_before_installing(name: str, job: str):
    steps: list[YamlDoc] = _jobs(name)[job]["steps"]
    names = [step.get("name") for step in steps]
    assert names.index("Pre-build command") < names.index("Install dependencies")
    hook = steps[names.index("Pre-build command")]
    assert hook["if"] == "inputs.pre_build_command != ''"
    # through the environment, never interpolated into the script
    assert "${{" not in hook["run"]
    assert hook["env"] == {
        "GH_TOKEN": "${{ secrets.GH_TOKEN }}",
        "PRE_BUILD_COMMAND": "${{ inputs.pre_build_command }}",
    }


def _site_step(name: str) -> YamlDoc:
    return next(step for step in _jobs("website.yml")["site-checks"]["steps"] if step.get("name") == name)


def test_site_checks_are_opt_in_and_gate_the_deploy_and_merge():
    jobs = _jobs("website.yml")
    assert "inputs.check_links || inputs.check_accessibility" in jobs["site-checks"]["if"]
    for name in ("deploy", "auto-merge"):
        # waits for the checks, but still runs when they're skipped
        assert "site-checks" in jobs[name]["needs"]
        assert "!failure()" in jobs[name]["if"]


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


def _debian_build_steps() -> list[YamlDoc]:
    doc = cast(YamlDoc, yaml.safe_load((WORKFLOWS_DIR / "debian.yml").read_text(encoding="utf-8")))
    return cast(list[YamlDoc], doc["jobs"]["build-deb"]["steps"])


def test_debian_build_installs_its_tools_pinned_and_verified():
    steps = _debian_build_steps()
    runs = "\n".join(str(step.get("run", "")) for step in steps)
    assert not re.search(r"\|\s*(ba)?sh\b", runs)
    assert "releases/latest" not in runs
    assert any(str(step.get("uses", "")).startswith("astral-sh/setup-uv@v") for step in steps)
    nfpm = next(step for step in steps if step.get("name") == "Install nfpm")
    assert re.fullmatch(r"\d+\.\d+\.\d+", nfpm["env"]["NFPM_VERSION"])
    assert re.fullmatch(r"[0-9a-f]{64}", nfpm["env"]["NFPM_SHA256"])


@pytest.mark.skipif(shutil.which("sha256sum") is None, reason="needs sha256sum")
def test_debian_build_refuses_an_nfpm_download_that_fails_its_checksum(tmp_path: Path):
    nfpm = next(step for step in _debian_build_steps() if step.get("name") == "Install nfpm")
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


def _secure_steps() -> list[YamlDoc]:
    doc = cast(YamlDoc, yaml.safe_load((WORKFLOWS_DIR / "quality.yml").read_text(encoding="utf-8")))
    return cast(list[YamlDoc], doc["jobs"]["secure"]["steps"])


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
    report = next(step for step in _secure_steps() if step.get("name") == "Report OSV findings")
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


def test_osv_scan_never_swallows_the_result():
    steps = _secure_steps()
    scan = next(step for step in steps if step.get("name") == "OSV Scan")
    report = next(step for step in steps if step.get("name") == "Report OSV findings")
    assert "|| true" not in scan["run"]
    assert report["env"]["OSV_ENFORCE"] == "${{ github.event_name == 'pull_request' }}"


needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="needs Node.js to run the github-script body")


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
@pytest.mark.parametrize(
    ("status", "results", "warned"), [(0, [], False), (128, [], False), (127, [], True), (1, None, True)]
)
def test_osv_report_passes_when_there_is_nothing_to_report(
    tmp_path: Path, status: int, results: list[YamlDoc] | None, *, warned: bool
):
    calls = _run_osv_report(tmp_path, status, results, enforce=True)
    assert calls["setFailed"] == []
    assert bool(calls["warning"]) is warned


# the author alone would merge someone else's push to Dependabot's branch, and the actor alone
# a pull request someone else opened that Dependabot then updated
def test_auto_merge_needs_dependabot_to_open_the_pull_request_and_make_its_latest_change():
    doc = cast(YamlDoc, yaml.safe_load((WORKFLOWS_DIR / "merge.yml").read_text(encoding="utf-8")))
    gate = str(doc["jobs"]["auto-merge"]["if"])
    assert "github.event.pull_request.user.login == 'dependabot[bot]' && " in gate
    assert "github.actor == 'dependabot[bot]' && " in gate
    assert "||" not in gate
