from __future__ import annotations

from typing import ClassVar

from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file, create_if_missing, remove_file

PYTEST_TOML = """\
[pytest]
testpaths = ["tests"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-branch",
    "--cov-report=term",
    "--cov-report=html",
    "--cov-report=json",
    "--junitxml=junit-report.xml",
]
forgepy_pass_with_no_tests = true
"""

# Keeps tests/ non-empty - an empty dir fails pyrightconfig's include and pytest's testpaths.
TEST_PLACEHOLDER = '''\
def test_placeholder() -> None:
    """Delete this once real tests exist."""
    assert True
'''


class TestingFeature(Feature):
    name: ClassVar[str] = "testing"

    def should_run(self, cfg: InitConfig) -> bool:
        return cfg.testing

    def apply(self, ctx: FeatureContext) -> bool:
        # Jython scripts aren't an installed package, so the tests import them from src/
        pytest_toml = PYTEST_TOML
        if ctx.cfg.jython:
            pytest_toml = pytest_toml.replace("[pytest]\n", '[pytest]\npythonpath = ["src"]\n')
        ok = create_file(ctx, "pytest.toml", pytest_toml)
        ok &= create_if_missing(ctx, "tests/test_placeholder.py", TEST_PLACEHOLDER)
        pj.set_task(ctx.pyproject, "test", "pytest", force=ctx.cfg.force)
        return ok

    def cleanup(self, ctx: FeatureContext) -> None:
        if not ctx.cfg.testing:
            remove_file(ctx, "pytest.toml")
