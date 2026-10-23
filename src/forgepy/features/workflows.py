from __future__ import annotations

import re
from dataclasses import replace
from typing import ClassVar

from forgepy import console
from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file, remove_file
from forgepy.templates import legacy as legacy_templates
from forgepy.templates import repository as repository_templates
from forgepy.templates import workflows as workflow_templates

INDEX_WORKFLOW = ".github/workflows/.index.yml"

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


def remove_old_workflows(ctx: FeatureContext) -> None:
    """Before .index.yml, forgepy generated index.yml; left in place, it runs every pipeline twice.

    One exactly as an earlier forgepy wrote it goes; one calling forgepy's pipelines that's been changed
    goes only with --force, as remove_file does; one calling none of them is the project's own.
    """
    for rel_path in legacy_templates.LEGACY_WORKFLOWS:
        path = ctx.cwd / rel_path
        if not ctx.fs.exists(path):
            continue
        try:
            content = ctx.fs.read_text(path)
        except (OSError, UnicodeDecodeError) as exc:
            console.warn(f"Left {rel_path}, which couldn't be read: {exc}")
            continue
        if legacy_templates.is_legacy_workflow(rel_path, content):
            remove_file(replace(ctx, cfg=replace(ctx.cfg, force=True)), rel_path)
        elif workflow_templates.calls_forgepy(content):
            if not ctx.cfg.force:
                console.warn(f"{rel_path} calls forgepy's old pipelines and has been changed since init wrote it.")
            remove_file(ctx, rel_path)
        else:
            console.warn(
                f"Left {rel_path}, which doesn't call forgepy's pipelines: "
                f"check it doesn't repeat {INDEX_WORKFLOW}'s jobs."
            )


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

        mode: workflow_templates.PipelineMode = (
            "library" if cfg.mode.is_library else "website" if cfg.mode.is_website else "service"
        )
        workflow = workflow_templates.index_workflow(
            workflow_templates.IndexWorkflowOptions(
                mode=mode,
                debian=cfg.debian,
                docker=cfg.docker,
                windows=cfg.windows,
                macos=cfg.macos,
                testing=cfg.testing,
                versioning=cfg.versioning,
                build=not cfg.jython,
            )
        )
        # only once .index.yml is written: a kept or failed one would leave the project with no CI, or the old one
        replacing = not ctx.fs.exists(ctx.cwd / INDEX_WORKFLOW) or cfg.force
        written = create_file(ctx, INDEX_WORKFLOW, workflow)
        if written and replacing:
            remove_old_workflows(ctx)
        return ok and written
