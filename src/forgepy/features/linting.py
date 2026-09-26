from __future__ import annotations

import json
from typing import ClassVar

from forgepy import pyproject as pj
from forgepy import templates
from forgepy.config import InitConfig
from forgepy.features.feature import (
    Feature,
    FeatureContext,
    create_file,
    remove_file,
    write_managed,
)

PRECOMMIT_CONFIG = """\
default_install_hook_types: [pre-commit, commit-msg, pre-push]
repos:
  - repo: local
    hooks:
      - id: ruff-check
        name: ruff check
        entry: uv run ruff check --fix
        language: system
        types: [python]
      - id: ruff-format
        name: ruff format
        entry: uv run ruff format
        language: system
        types: [python]
      - id: basedpyright
        name: basedpyright
        entry: uv run basedpyright
        language: system
        types: [python]
        pass_filenames: false
        stages: [pre-push]
      - id: forgepy-sync-check
        name: forgepy sync --check
        entry: uv run forgepy sync --check
        language: system
        pass_filenames: false
{commitizen_hook}"""

COMMITIZEN_HOOK = """\
      - id: commitizen
        name: commitizen check
        entry: uv run cz check --commit-msg-file
        language: system
        stages: [commit-msg]
"""


class LintingFeature(Feature):
    name: ClassVar[str] = "linting"

    def should_run(self, cfg: InitConfig) -> bool:
        return cfg.linting

    def apply(self, ctx: FeatureContext) -> bool:
        ok = True
        ok &= write_managed(ctx, ".forgepy/ruff.toml", templates.load_config("ruff.toml"))
        ok &= create_file(
            ctx,
            "ruff.toml",
            f'extend = ".forgepy/ruff.toml"\n'
            f'target-version = "py{ctx.cfg.python_version.replace(".", "")}"\n\n'
            f"[lint.per-file-ignores]\n"
            f'"tests/**" = ["S101", "S603", "S607"]\n',
        )
        ok &= write_managed(
            ctx,
            ".forgepy/pyrightconfig.json",
            templates.load_config("pyrightconfig.json"),
        )
        # Only include paths BaseFeature/TestingFeature actually create - website mode has
        # no src/, and --no-testing skips tests/, so basedpyright would exit nonzero on a
        # fresh scaffold if we always claimed both existed.
        include_paths: list[str] = []
        if not ctx.cfg.mode.is_website:
            include_paths.append("src")
        if ctx.cfg.testing:
            include_paths.append("tests")

        pyrightconfig = {
            "extends": ".forgepy/pyrightconfig.json",
            "include": include_paths,
            "venvPath": ".",
            "venv": ".venv",
        }
        ok &= create_file(ctx, "pyrightconfig.json", json.dumps(pyrightconfig, indent=2) + "\n")

        commitizen_hook = COMMITIZEN_HOOK if ctx.cfg.versioning else ""
        ok &= create_file(
            ctx,
            ".pre-commit-config.yaml",
            PRECOMMIT_CONFIG.format(commitizen_hook=commitizen_hook),
        )

        pj.set_shell_task(
            ctx.pyproject,
            "lint",
            "ruff check --fix . && ruff format .",
            force=ctx.cfg.force,
        )
        pj.set_task(ctx.pyproject, "format", "ruff format .", force=ctx.cfg.force)
        pj.set_task(ctx.pyproject, "security", "osv-scanner scan -r .", force=ctx.cfg.force)
        pj.set_task(ctx.pyproject, "hooks", "pre-commit install", force=ctx.cfg.force)
        pj.set_task(ctx.pyproject, "sync-check", "forgepy sync --check", force=ctx.cfg.force)
        pj.ensure_dev_dependency(ctx.pyproject, "forgepy[toolchain]")

        return ok

    def cleanup(self, ctx: FeatureContext) -> None:
        if ctx.cfg.linting:
            return
        remove_file(ctx, "ruff.toml")
        remove_file(ctx, ".forgepy/ruff.toml")
        remove_file(ctx, "pyrightconfig.json")
        remove_file(ctx, ".forgepy/pyrightconfig.json")
        remove_file(ctx, ".pre-commit-config.yaml")
