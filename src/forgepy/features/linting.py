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
{vermin_hook}{commitizen_hook}"""

COMMITIZEN_HOOK = """\
      - id: commitizen
        name: commitizen check
        entry: uv run cz check --commit-msg-file
        language: system
        stages: [commit-msg]
"""

VERMIN_HOOK = """\
      - id: vermin
        name: vermin (Jython 2.7 compatibility)
        entry: uv run poe compat
        language: system
        files: ^src/
        types: [python]
        pass_filenames: false
"""

# vermin reads no pyproject.toml settings, so they live in the task. typing is excluded as the
# scripts import it only under `if MYPY:`, for type comments; Jython never runs that import.
# check-jython finds the commas after *args/**kwargs that ruff format adds and vermin can't see.
COMPAT_TASK = (
    "vermin --target=2.7- --violations --no-tips --eval-annotations --exclude typing src && forgepy check-jython src"
)


class LintingFeature(Feature):
    name: ClassVar[str] = "linting"

    def should_run(self, cfg: InitConfig) -> bool:
        return cfg.linting

    def apply(self, ctx: FeatureContext) -> bool:
        ok = True
        ok &= write_managed(ctx, ".forgepy/ruff.toml", templates.load_config("ruff.toml"))
        if ctx.cfg.jython:
            # the Jython base sets its own target version, the oldest ruff supports
            ok &= write_managed(ctx, ".forgepy/ruff-jython.toml", templates.load_config("ruff-jython.toml"))
            ruff_base = 'extend = ".forgepy/ruff-jython.toml"\n'
        else:
            ruff_base = (
                f'extend = ".forgepy/ruff.toml"\ntarget-version = "py{ctx.cfg.python_version.replace(".", "")}"\n'
            )
        ok &= create_file(
            ctx,
            "ruff.toml",
            f'{ruff_base}\n[lint.per-file-ignores]\n"tests/**" = ["S101", "S603", "S607"]\n',
        )
        ok &= write_managed(
            ctx,
            ".forgepy/pyrightconfig.json",
            templates.load_config("pyrightconfig.json"),
        )
        # Only include paths that actually exist - website mode skips src/, --no-testing skips tests/.
        include_paths: list[str] = []
        if not ctx.cfg.mode.is_website:
            include_paths.append("src")
        if ctx.cfg.testing:
            include_paths.append("tests")

        pyrightconfig: dict[str, object] = {
            "extends": ".forgepy/pyrightconfig.json",
            "include": include_paths,
            "venvPath": ".",
            "venv": ".venv",
        }
        if ctx.cfg.jython:
            # Python 2 code can only annotate with type comments, and imports their names under
            # `if MYPY:`, which Jython skips but basedpyright follows
            pyrightconfig["defineConstant"] = {"MYPY": True}
            pyrightconfig["reportTypeCommentUsage"] = False
        ok &= create_file(ctx, "pyrightconfig.json", json.dumps(pyrightconfig, indent=2) + "\n")

        commitizen_hook = COMMITIZEN_HOOK if ctx.cfg.versioning else ""
        ok &= create_file(
            ctx,
            ".pre-commit-config.yaml",
            PRECOMMIT_CONFIG.format(vermin_hook=VERMIN_HOOK if ctx.cfg.jython else "", commitizen_hook=commitizen_hook),
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
        if ctx.cfg.jython:
            pj.ensure_dev_dependency(ctx.pyproject, "vermin>=1.8")
            pj.set_shell_task(ctx.pyproject, "compat", COMPAT_TASK, force=ctx.cfg.force)

        return ok

    def cleanup(self, ctx: FeatureContext) -> None:
        if not ctx.cfg.jython:
            # CI runs the Jython check wherever this base exists
            remove_file(ctx, ".forgepy/ruff-jython.toml")
        if ctx.cfg.linting:
            return
        remove_file(ctx, "ruff.toml")
        remove_file(ctx, ".forgepy/ruff.toml")
        remove_file(ctx, "pyrightconfig.json")
        remove_file(ctx, ".forgepy/pyrightconfig.json")
        remove_file(ctx, ".pre-commit-config.yaml")
