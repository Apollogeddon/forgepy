from __future__ import annotations

import json
from typing import ClassVar

from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features.feature import Feature, FeatureContext, create_file, remove_file


class VersioningFeature(Feature):
    name: ClassVar[str] = "versioning"

    def should_run(self, cfg: InitConfig) -> bool:
        return cfg.versioning

    def apply(self, ctx: FeatureContext) -> bool:
        # uv.lock records the PEP 503 normalized name, e.g. My_Project as my-project
        project_name = pj.normalize_project_name(pj.project_name(ctx.pyproject, ctx.cwd))

        manifest = {".": "0.1.0"}
        config = {
            "packages": {
                ".": {
                    "release-type": "python",
                    "extra-files": [
                        # release-please's TOML parser wraps each value, so the filter matches on name.value
                        {
                            "type": "toml",
                            "path": "uv.lock",
                            "jsonpath": f"$.package[?(@.name.value=='{project_name}')].version",
                        }
                    ],
                }
            }
        }

        ok = create_file(ctx, ".github/.release.json", json.dumps(manifest, indent=2) + "\n")
        ok &= create_file(ctx, ".github/release.json", json.dumps(config, indent=2) + "\n")

        pj.set_table_if_absent(
            ctx.pyproject,
            ("tool", "commitizen"),
            {"name": "cz_conventional_commits", "tag_format": "v$version"},
            force=ctx.cfg.force,
        )

        return ok

    def cleanup(self, ctx: FeatureContext) -> None:
        if not ctx.cfg.versioning:
            remove_file(ctx, ".github/.release.json")
            remove_file(ctx, ".github/release.json")
