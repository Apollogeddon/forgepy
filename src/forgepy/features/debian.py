from __future__ import annotations

from typing import ClassVar

from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file, remove_file
from forgepy.templates import debian as debian_templates


def _deb_name(ctx: FeatureContext) -> str:
    return pj.normalize_project_name(pj.project_name(ctx.pyproject, ctx.cwd))


class DebianFeature(Feature):
    name: ClassVar[str] = "debian"

    def should_run(self, cfg: InitConfig) -> bool:
        return cfg.debian

    def apply(self, ctx: FeatureContext) -> bool:
        deb_name = _deb_name(ctx)
        module_name = pj.package_module_name(ctx.pyproject, ctx.cwd)

        def render(template: str) -> str:
            return debian_templates.render(
                template,
                deb_name=deb_name,
                module_name=module_name,
                python_version=ctx.cfg.python_version,
            )

        ok = create_file(ctx, "nfpm.yaml", render(debian_templates.NFPM_YAML))
        ok &= create_file(ctx, f"packaging/{deb_name}.service", render(debian_templates.SYSTEMD_UNIT))
        ok &= create_file(ctx, "packaging/postinstall.sh", render(debian_templates.POSTINSTALL_SH))
        ok &= create_file(ctx, "packaging/build_deb.py", debian_templates.BUILD_DEB_PY)

        pj.set_shell_task(
            ctx.pyproject,
            "build-deb",
            "uv venv --relocatable --no-managed-python .venv && "
            "uv sync --locked --no-dev --no-editable && "
            "python packaging/build_deb.py",
            force=ctx.cfg.force,
        )

        return ok

    def cleanup(self, ctx: FeatureContext) -> None:
        if not ctx.cfg.debian:
            deb_name = _deb_name(ctx)
            remove_file(ctx, "nfpm.yaml")
            remove_file(ctx, f"packaging/{deb_name}.service")
            remove_file(ctx, "packaging/postinstall.sh")
            remove_file(ctx, "packaging/build_deb.py")
