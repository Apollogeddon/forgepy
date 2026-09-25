from __future__ import annotations

from typing import ClassVar

from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file

PRIVATE_CLASSIFIER = "Private :: Do Not Upload"


class BaseFeature(Feature):
    name: ClassVar[str] = "base"

    def should_run(self, cfg: InitConfig) -> bool:
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

        return create_file(ctx, ".python-version", f"{ctx.cfg.python_version}\n")
