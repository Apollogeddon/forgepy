from __future__ import annotations

from typing import ClassVar

import tomlkit

from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file, create_if_missing
from forgepy.templates import package as package_templates
from forgepy.templates import repository as repository_templates

PRIVATE_CLASSIFIER = "Private :: Do Not Upload"
# forgepy isn't on PyPI; resolving it from git also stops a same-named PyPI package being installed instead
FORGEPY_GIT = "https://github.com/apollogeddon/forgepy"


class BaseFeature(Feature):
    name: ClassVar[str] = "base"

    def should_run(self, cfg: InitConfig) -> bool:  # noqa: ARG002 - Feature interface
        return True

    def apply(self, ctx: FeatureContext) -> bool:
        if ctx.cfg.packaged:
            pj.set_table_if_absent(
                ctx.pyproject,
                ("build-system",),
                {"requires": ["uv_build>=0.7,<0.13"], "build-backend": "uv_build"},
                force=ctx.cfg.force,
            )

        # The toolchain provides ruff/basedpyright/pytest, which CI runs whichever features are enabled.
        pj.ensure_dev_dependency(ctx.pyproject, "forgepy[toolchain]")
        source = tomlkit.inline_table()
        source["git"] = FORGEPY_GIT
        # never overwrite an existing source (e.g. a local path), even with --force
        pj.set_key_if_absent(ctx.pyproject, ("tool", "uv", "sources"), "forgepy", source, force=False)

        if not ctx.cfg.mode.is_library:
            pj.ensure_classifier(ctx.pyproject, PRIVATE_CLASSIFIER)

        ok = create_file(ctx, ".editorconfig", repository_templates.EDITORCONFIG)
        if not ctx.cfg.packaged:
            # A docs site has no importable module, and Jython scripts aren't a Python 3 package,
            # so uv must not try to build/install it: it only installs the dev tools.
            pj.set_key_if_absent(ctx.pyproject, ("tool", "uv"), "package", False, force=ctx.cfg.force)
        if ctx.cfg.jython:
            project_name = pj.project_name(ctx.pyproject, ctx.cwd)
            ok &= create_if_missing(
                ctx,
                "src/hello.py",
                package_templates.render(package_templates.JYTHON_SCRIPT_PY, project_name=project_name),
            )
        elif ctx.cfg.packaged:
            # uv_build requires the module to exist at `uv sync`/`uv build` time.
            module_name = pj.package_module_name(ctx.pyproject, ctx.cwd)
            project_name = pj.project_name(ctx.pyproject, ctx.cwd)
            ok &= create_if_missing(
                ctx,
                f"src/{module_name}/__init__.py",
                package_templates.render(package_templates.INIT_PY, project_name=project_name),
            )
            if ctx.cfg.mode.is_backend:
                ok &= create_if_missing(
                    ctx,
                    f"src/{module_name}/__main__.py",
                    package_templates.render(package_templates.MAIN_PY, project_name=project_name),
                )

        ok &= create_file(ctx, ".python-version", f"{ctx.cfg.python_version}\n")
        return ok
