from __future__ import annotations

from typing import ClassVar

from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file, create_if_missing
from forgepy.templates import package as package_templates

PRIVATE_CLASSIFIER = "Private :: Do Not Upload"


class BaseFeature(Feature):
    name: ClassVar[str] = "base"

    def should_run(self, cfg: InitConfig) -> bool:  # noqa: ARG002 - Feature interface
        return True

    def apply(self, ctx: FeatureContext) -> bool:
        pj.set_table_if_absent(
            ctx.pyproject,
            ("build-system",),
            {"requires": ["uv_build>=0.7,<0.9"], "build-backend": "uv_build"},
            force=ctx.cfg.force,
        )

        if not ctx.cfg.mode.is_library:
            pj.ensure_classifier(ctx.pyproject, PRIVATE_CLASSIFIER)

        ok = True
        if ctx.cfg.mode.is_website:
            # A docs site has no importable module, so uv must not try to build/install it.
            pj.set_key_if_absent(ctx.pyproject, ("tool", "uv"), "package", False, force=ctx.cfg.force)
        else:
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
