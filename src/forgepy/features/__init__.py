from forgepy.features.base import BaseFeature
from forgepy.features.build import BuildFeature
from forgepy.features.debian import DebianFeature
from forgepy.features.docker import DockerFeature
from forgepy.features.feature import Feature, FeatureContext
from forgepy.features.linting import LintingFeature
from forgepy.features.testing import TestingFeature
from forgepy.features.versioning import VersioningFeature
from forgepy.features.workflows import WorkflowFeature

PIPELINE: tuple[Feature, ...] = (
    BaseFeature(),
    LintingFeature(),
    BuildFeature(),
    TestingFeature(),
    VersioningFeature(),
    DockerFeature(),
    DebianFeature(),
    WorkflowFeature(),
)

__all__ = ["PIPELINE", "Feature", "FeatureContext"]
