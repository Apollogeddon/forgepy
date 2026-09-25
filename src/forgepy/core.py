from __future__ import annotations

from forgepy import console
from forgepy import pyproject as pj
from forgepy.config import InitConfig
from forgepy.features import PIPELINE, FeatureContext
from forgepy.utils.filesystem import FileSystem, LocalFileSystem


def init(cfg: InitConfig, fs: FileSystem | None = None) -> int:
    fs = fs or LocalFileSystem()
    cwd = cfg.target

    console.info(
        f"forgepy init — mode={cfg.mode.value}" + (" (dry run)" if cfg.dry_run else "")
    )
    if cfg.dry_run:
        console.warn("DRY RUN MODE — no files will be written")

    active = [f.name for f in PIPELINE if f.should_run(cfg)]
    console.info(f"Active features: {', '.join(active) if active else 'none'}")

    try:
        doc = pj.load_or_create(fs, cwd, cfg.python_version)
    except pj.PyprojectError as exc:
        console.err(str(exc))
        return 1

    ctx = FeatureContext(cwd=cwd, cfg=cfg, fs=fs, pyproject=doc)

    had_errors = False
    for feature in PIPELINE:
        if feature.should_run(cfg) and not feature.apply(ctx):
            had_errors = True

    if cfg.dry_run:
        console.dry("Would update pyproject.toml")
    else:
        pj.save(fs, cwd, doc)

    for feature in PIPELINE:
        feature.cleanup(ctx)

    if had_errors:
        console.err("forgepy init finished with errors")
        return 1

    console.ok("forgepy init complete")
    console.info("Next steps: uv sync && uv run poe hooks")
    return 0
