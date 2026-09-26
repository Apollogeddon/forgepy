from __future__ import annotations

from typing import ClassVar

from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file
from forgepy.templates import workflows as workflow_templates


class WorkflowFeature(Feature):
    name: ClassVar[str] = "workflows"

    def should_run(self, cfg: InitConfig) -> bool:  # noqa: ARG002 - Feature interface
        return True

    def apply(self, ctx: FeatureContext) -> bool:
        cfg = ctx.cfg
        if cfg.debian:
            template = workflow_templates.DEBIAN_WORKFLOW
        elif cfg.mode.is_library:
            template = workflow_templates.LIBRARY_WORKFLOW
        elif cfg.mode.is_website:
            template = workflow_templates.WEBSITE_WORKFLOW
        else:
            template = workflow_templates.SERVICE_WORKFLOW

        content = workflow_templates.render(template, python_version=cfg.python_version)
        return create_file(ctx, ".github/workflows/index.yml", content)
