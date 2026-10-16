from __future__ import annotations

from dataclasses import replace

from forgepy import console
from forgepy import pyproject as pj
from forgepy.config import MIN_PYTHON_MINOR, InitConfig, valid_python_version
from forgepy.features import PIPELINE, FeatureContext
from forgepy.utils.filesystem import FileSystem, LocalFileSystem

EXIT_INVALID_CONFIG = 2


def init(cfg: InitConfig, fs: FileSystem | None = None) -> int:
    fs = fs or LocalFileSystem()
    cwd = cfg.target

    if cfg.python_version is None:
        pinned = pj.project_python_version(fs, cwd)
        if pinned is not None and not valid_python_version(pinned):
            console.err(
                f"The project pins Python {pinned!r} (.python-version or requires-python), which forgepy can't "
                f"target: pass --python with a version from 3.{MIN_PYTHON_MINOR} up"
            )
            return EXIT_INVALID_CONFIG
        cfg = replace(cfg, python_version=pinned)

    errors = cfg.validate()
    if errors:
        for error in errors:
            console.err(error)
        return EXIT_INVALID_CONFIG

    console.info(f"forgepy init — mode={cfg.mode.value}" + (" (dry run)" if cfg.dry_run else ""))
    if cfg.dry_run:
        console.warn("DRY RUN MODE — no files will be written")

    active = [f.name for f in PIPELINE if f.should_run(cfg)]
    console.info(f"Active features: {', '.join(active) if active else 'none'}")

    try:
        doc = pj.load_or_create(fs, cwd, cfg.python)
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
