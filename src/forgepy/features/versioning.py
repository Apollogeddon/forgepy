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
        project_name = ctx.pyproject.get("project", {}).get("name", ctx.cwd.name)

        manifest = {".": "0.1.0"}
        config = {
            "packages": {
                ".": {
                    "release-type": "python",
                    "extra-files": [
                        {
                            "type": "toml",
                            "path": "uv.lock",
                            "jsonpath": f"$.package[?(@.name=='{project_name}')].version",
                        }
                    ],
                }
            }
        }

        ok = create_file(
            ctx, ".release-please-manifest.json", json.dumps(manifest, indent=2) + "\n"
        )
        ok &= create_file(
            ctx, "release-please-config.json", json.dumps(config, indent=2) + "\n"
        )

        pj.set_table_if_absent(
            ctx.pyproject,
            ("tool", "commitizen"),
            {"name": "cz_conventional_commits", "tag_format": "v$version"},
            force=ctx.cfg.force,
        )

        return ok

    def cleanup(self, ctx: FeatureContext) -> None:
        if not ctx.cfg.versioning:
            remove_file(ctx, ".release-please-manifest.json")
            remove_file(ctx, "release-please-config.json")
