from __future__ import annotations

from typing import ClassVar

from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file, remove_file

PYTEST_TOML = """\
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-branch --cov-report=term --cov-report=html --cov-report=json --junitxml=junit-report.xml"
forgepy_pass_with_no_tests = true
"""


class TestingFeature(Feature):
    name: ClassVar[str] = "testing"

    def should_run(self, cfg: InitConfig) -> bool:
        return cfg.testing

    def apply(self, ctx: FeatureContext) -> bool:
        ok = create_file(ctx, "pytest.toml", PYTEST_TOML)
        pj.set_task(ctx.pyproject, "test", "pytest", force=ctx.cfg.force)
        return ok

    def cleanup(self, ctx: FeatureContext) -> None:
        if not ctx.cfg.testing:
            remove_file(ctx, "pytest.toml")
