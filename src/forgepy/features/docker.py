from __future__ import annotations

from typing import ClassVar

from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file, remove_file
from forgepy.templates import docker as docker_templates


class DockerFeature(Feature):
    name: ClassVar[str] = "docker"

    def should_run(self, cfg: InitConfig) -> bool:
        return cfg.docker

    def apply(self, ctx: FeatureContext) -> bool:
        package_name = pj.package_module_name(ctx.pyproject, ctx.cwd)
        template = (
            docker_templates.DOCKERFILE_WEBSITE if ctx.cfg.mode.is_website else docker_templates.DOCKERFILE_BACKEND
        )
        dockerfile = docker_templates.render(
            template,
            python_version=ctx.cfg.python_version,
            package_name=package_name,
        )
        ok = create_file(ctx, "Dockerfile", dockerfile)
        ok &= create_file(ctx, ".dockerignore", docker_templates.DOCKERIGNORE)

        run_cmd = (
            "docker run --rm -p 8080:80 " + package_name
            if ctx.cfg.mode.is_website
            else f"docker run --rm {package_name}"
        )
        pj.set_task(
            ctx.pyproject,
            "docker-build",
            f"docker build -t {package_name} .",
            force=ctx.cfg.force,
        )
        pj.set_task(ctx.pyproject, "docker-run", run_cmd, force=ctx.cfg.force)

        return ok

    def cleanup(self, ctx: FeatureContext) -> None:
        if not ctx.cfg.docker:
            remove_file(ctx, "Dockerfile")
            remove_file(ctx, ".dockerignore")
