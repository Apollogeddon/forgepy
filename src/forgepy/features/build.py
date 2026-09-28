from __future__ import annotations

from typing import ClassVar

from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file
from forgepy.templates import mkdocs as mkdocs_templates


class BuildFeature(Feature):
    name: ClassVar[str] = "build"

    def should_run(self, cfg: InitConfig) -> bool:  # noqa: ARG002 - Feature interface
        return True

    def apply(self, ctx: FeatureContext) -> bool:
        force = ctx.cfg.force

        if ctx.cfg.mode.is_website:
            project_name = pj.project_name(ctx.pyproject, ctx.cwd)

            ok = create_file(
                ctx,
                "mkdocs.yml",
                mkdocs_templates.render(mkdocs_templates.MKDOCS_YML, project_name=project_name),
            )
            ok &= create_file(
                ctx,
                "docs/index.md",
                mkdocs_templates.render(mkdocs_templates.DOCS_INDEX_MD, project_name=project_name),
            )

            # Zensical builds MkDocs 1.x projects; MkDocs itself is unmaintained and 2.0 breaks Material
            pj.ensure_dev_dependency(ctx.pyproject, "zensical>=0.0.66,<0.1")
            pj.set_task(ctx.pyproject, "dev", "zensical serve", force=force)
            pj.set_task(ctx.pyproject, "build", "zensical build", force=force)
            pj.set_task(ctx.pyproject, "type", "basedpyright", force=force)
            return ok
        package_name = pj.package_module_name(ctx.pyproject, ctx.cwd)
        pj.set_task(ctx.pyproject, "build", "uv build", force=force)
        pj.set_task(ctx.pyproject, "type", "basedpyright", force=force)
        if ctx.cfg.mode.is_backend:
            pj.set_task(ctx.pyproject, "start", f"python -m {package_name}", force=force)
            pj.set_task(
                ctx.pyproject,
                "watch",
                f"watchmedo auto-restart -- python -m {package_name}",
                force=force,
            )
        if ctx.cfg.mode.is_library:
            pj.set_task(
                ctx.pyproject,
                "check-dist",
                "validate-pyproject pyproject.toml",
                force=force,
            )

        return True
