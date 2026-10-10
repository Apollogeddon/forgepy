from __future__ import annotations

import re
from typing import ClassVar

from forgepy import console
from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file
from forgepy.templates import repository as repository_templates
from forgepy.templates import workflows as workflow_templates

_GITHUB_OWNER = re.compile(r"github\.com[:/]([A-Za-z0-9][A-Za-z0-9-]*)/")


def github_owner(ctx: FeatureContext) -> str | None:
    """The GitHub account the project lives under, from pyproject's project.urls or the git
    remote, so CODEOWNERS can name it. None until the project has a GitHub remote."""
    for url in pj.project_urls(ctx.pyproject):
        if match := _GITHUB_OWNER.search(url):
            return match.group(1)

    git_config = ctx.cwd / ".git" / "config"
    if not ctx.fs.exists(git_config):
        return None
    for section in re.split(r"^\[", ctx.fs.read_text(git_config), flags=re.MULTILINE):
        if section.startswith('remote "origin"') and (match := _GITHUB_OWNER.search(section)):
            return match.group(1)
    return None


class WorkflowFeature(Feature):
    name: ClassVar[str] = "workflows"

    def should_run(self, cfg: InitConfig) -> bool:  # noqa: ARG002 - Feature interface
        return True

    def apply(self, ctx: FeatureContext) -> bool:
        cfg = ctx.cfg
        ok = create_file(ctx, ".github/dependabot.yml", repository_templates.dependabot(docker=cfg.docker))
        if owner := github_owner(ctx):
            ok &= create_file(
                ctx, ".github/CODEOWNERS", repository_templates.CODEOWNERS.replace("__FORGEPY_OWNER__", owner)
            )
        else:
            console.info("No GitHub remote yet, so no .github/CODEOWNERS. Run init again once the project has one.")

        if cfg.debian:
            template = workflow_templates.DEBIAN_WORKFLOW
        elif cfg.mode.is_library:
            template = workflow_templates.LIBRARY_WORKFLOW
        elif cfg.mode.is_website:
            template = workflow_templates.WEBSITE_WORKFLOW
        else:
            template = workflow_templates.SERVICE_WORKFLOW

        inputs: dict[str, bool] = {}
        if cfg.jython:
            # nothing to build: the scripts are deployed as they are
            inputs["run_build"] = False
        if not cfg.testing:
            inputs["run_tests"] = False
        if not cfg.versioning:
            inputs["enable_versioning"] = False
        content = workflow_templates.render(
            template, python_version=cfg.python_version, docker=cfg.docker, inputs=inputs
        )
        ok &= create_file(ctx, ".github/workflows/index.yml", content)
        return ok
