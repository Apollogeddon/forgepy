from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# The generated .github/workflows/.index.yml: each job calls one forgepy pipeline, so a run page reads
# <pipeline> / <stage>. Pull requests run the checks, main runs release-please and, on a release, the checks
# again before shipping, and patch upgrades vulnerable dependencies weekly, on a manual run and after a
# Dependabot merge.

PipelineMode = Literal["library", "service", "website"]

FORGEPY_WORKFLOWS = "apollogeddon/forgepy/.github/workflows"

# Plain text, not an f-string or string.Template: GitHub Actions' "${{ ... }}" collides with both
_HEADER = """\
name: index

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]
  workflow_dispatch:
  # sent by the merge pipeline, as a merge it makes starts no push run on main
  repository_dispatch:
    types: [auto-merged]
  # weekly, for the patch pipeline, which a manual run and a Dependabot merge start too
  schedule:
    - cron: '17 3 * * 1'

concurrency:
  # a pull request's newer run replaces its older one; every other run has a group of its own, so a run on
  # main, running or queued, is never cancelled and a release is never created without being published
  group: ${{ github.workflow }}-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true

jobs:
"""

_RELEASED = "needs.version.outputs.new_release_published == 'true'"


def _expr(expression: str) -> str:
    return "${{ " + expression + " }}"


@dataclass(frozen=True)
class IndexWorkflowOptions:
    mode: PipelineMode
    debian: bool = False
    docker: bool = False
    testing: bool = True
    versioning: bool = True
    # a --jython project's scripts are deployed as they are, so there's nothing to build
    build: bool = True


@dataclass
class PipelineJob:
    id: str
    pipeline: str
    permissions: dict[str, str]
    comment: str = ""
    needs: list[str] = field(default_factory=list[str])
    condition: str = ""
    inputs: dict[str, str | bool] = field(default_factory=dict[str, str | bool])

    def render(self) -> str:
        lines = [f"  # {self.comment}"] if self.comment else []
        lines.append(f"  {self.id}:")
        if self.needs:
            lines.append(f"    needs: {self.needs[0] if len(self.needs) == 1 else '[' + ', '.join(self.needs) + ']'}")
        if self.condition:
            lines.append(f"    if: {_expr(self.condition)}")
        lines.append(f"    uses: {FORGEPY_WORKFLOWS}/{self.pipeline}.yml@main")
        if self.inputs:
            lines.append("    with:")
            lines.extend(
                f"      {key}: {str(value).lower() if isinstance(value, bool) else value}"
                for key, value in self.inputs.items()
            )
        lines.append("    permissions:")
        lines.extend(f"      {key}: {value}" for key, value in self.permissions.items())
        return "\n".join(lines) + "\n"


def pipeline_inputs(cfg: IndexWorkflowOptions) -> dict[str, str | bool]:
    """Disabled standard features become pipeline inputs, so CI doesn't run what the project doesn't have.

    --no-testing turns off the test stage and --jython the build stage. --no-versioning leaves out the
    version job, and with it the release testing and publish; --no-linting needs nothing, as forgepy's
    toolchain always installs ruff and basedpyright, which run on their defaults without a project config.
    """
    inputs: dict[str, str | bool] = {}
    if not cfg.testing:
        inputs["run_tests"] = False
    if not cfg.build:
        inputs["run_build"] = False
    return inputs


def _checks_passed(checks: str) -> str:
    return f"!cancelled() && needs.{checks}.result == 'success'"


def index_workflow(cfg: IndexWorkflowOptions) -> str:
    checks = cfg.mode
    jobs: list[PipelineJob] = []

    if cfg.versioning:
        jobs.append(
            PipelineJob(
                id="version",
                comment="release-please, on main",
                condition="github.event_name != 'pull_request' && github.event_name != 'schedule'",
                pipeline="version",
                permissions={"contents": "write", "pull-requests": "write"},
            )
        )

    jobs.append(
        PipelineJob(
            id=checks,
            comment="a pull request's checks, and on main a release's, before it ships"
            if cfg.versioning
            else "the checks, on pull requests and every push to main",
            needs=["version"] if cfg.versioning else [],
            condition=f"!cancelled() && (github.event_name == 'pull_request' || {_RELEASED})"
            if cfg.versioning
            else "github.event_name != 'schedule'",
            pipeline=checks,
            inputs=pipeline_inputs(cfg),
            # Gitleaks comments on the pull request it finds a secret in
            permissions={"contents": "read", "pull-requests": "write"},
        )
    )

    check_jobs = [checks]
    if cfg.debian:
        jobs.append(
            PipelineJob(
                id="debian",
                needs=[checks],
                condition=_checks_passed(checks),
                pipeline="debian",
                permissions={"contents": "read"},
            )
        )
        check_jobs.append("debian")
    if cfg.docker:
        # a job of its own after the checks, so projects without Docker don't carry a permanently skipped
        # one: it builds on pull requests, and builds and pushes on a release
        jobs.append(
            PipelineJob(
                id="docker",
                needs=["version", checks] if cfg.versioning else [checks],
                condition=_checks_passed(checks),
                pipeline="docker",
                inputs={"push": _expr(_RELEASED), "version": _expr("needs.version.outputs.version")}
                if cfg.versioning
                else {},
                permissions={"contents": "read", "packages": "write"},
            )
        )
        check_jobs.append("docker")

    if cfg.versioning and cfg.mode == "library":
        jobs.append(
            PipelineJob(
                id="publish",
                comment="the release's package, to PyPI through Trusted Publishing",
                needs=["version", checks],
                condition=f"{_checks_passed(checks)} && {_RELEASED}",
                pipeline="publish",
                permissions={"contents": "read", "id-token": "write"},
            )
        )
    elif cfg.versioning and cfg.debian:
        jobs.append(
            PipelineJob(
                id="publish",
                comment="the release's .deb, attached to the GitHub release",
                needs=["version", "debian"],
                condition=f"{_checks_passed('debian')} && {_RELEASED}",
                pipeline="publish",
                inputs={
                    "package": False,
                    "assets": "debian-package",
                    "tag_name": _expr("needs.version.outputs.tag_name"),
                },
                # id-token: write only because the skipped package stage asks for it, which GitHub checks all the same
                permissions={"contents": "write", "id-token": "write"},
            )
        )

    if cfg.mode == "website":
        jobs.append(
            PipelineJob(
                id="pages",
                comment="a release, to GitHub Pages" if cfg.versioning else "every change to main, to GitHub Pages",
                needs=["version", checks] if cfg.versioning else [checks],
                condition=f"{_checks_passed(checks)} && {_RELEASED}"
                if cfg.versioning
                else "github.ref == 'refs/heads/main' && github.event_name != 'pull_request'",
                pipeline="pages",
                permissions={"pages": "write", "id-token": "write"},
            )
        )

    jobs.append(
        PipelineJob(
            id="patch",
            comment=(
                "weekly, on a manual run and after a Dependabot merge: "
                "forgepy's configs refreshed and vulnerable packages upgraded on main"
            ),
            condition=(
                "github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'"
                " || github.event_name == 'repository_dispatch'"
            ),
            pipeline="patch",
            permissions={"contents": "write"},
        )
    )

    jobs.append(
        PipelineJob(
            id="merge",
            comment="Dependabot's pull requests: a review request, and a squash merge when the checks passed",
            needs=check_jobs,
            condition="!cancelled() && github.event_name == 'pull_request' && "
            "github.event.pull_request.user.login == 'dependabot[bot]'",
            pipeline="merge",
            inputs={
                "checks_passed": _expr("!contains(needs.*.result, 'failure') && !contains(needs.*.result, 'cancelled')")
            },
            permissions={"contents": "write", "pull-requests": "write"},
        )
    )

    return _HEADER + "\n".join(job.render() for job in jobs)


_CALLS_FORGEPY = re.compile(r"apollogeddon/forgepy/\.github/workflows/", re.IGNORECASE)


def calls_forgepy(content: str) -> bool:
    """A workflow that calls forgepy's pipelines, rather than one of the project's own."""
    return _CALLS_FORGEPY.search(content) is not None
