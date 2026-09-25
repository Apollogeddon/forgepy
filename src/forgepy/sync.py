from __future__ import annotations

from pathlib import Path

from forgepy import console, templates
from forgepy.utils.filesystem import FileSystem, LocalFileSystem

# Maps each managed snapshot's project-relative path to the shipped config it
# mirrors (forgepy.configs/<name>). Extend this as forgepy ships more base configs.
MANAGED_CONFIGS: dict[str, str] = {
    ".forgepy/ruff.toml": "ruff.toml",
    ".forgepy/pyrightconfig.json": "pyrightconfig.json",
}


def sync(cwd: Path, *, check: bool = False, fs: FileSystem | None = None) -> int:
    fs = fs or LocalFileSystem()
    contents = {rel_path: templates.load_config(name) for rel_path, name in MANAGED_CONFIGS.items()}

    drifted = [
        rel_path
        for rel_path, content in contents.items()
        if not fs.exists(cwd / rel_path) or fs.read_text(cwd / rel_path) != content
    ]

    if check:
        if drifted:
            for rel_path in drifted:
                console.warn(f"{rel_path} is out of date")
            console.err(f"{len(drifted)} managed config(s) out of date - run `forgepy sync` to refresh")
            return 1
        console.ok("All managed configs are up to date")
        return 0

    if not drifted:
        console.info("All managed configs already up to date")
        return 0

    try:
        for rel_path in drifted:
            target = cwd / rel_path
            parent = target.parent
            if not fs.exists(parent):
                fs.mkdir(parent, parents=True)
            fs.write_text(target, contents[rel_path])
            console.ok(f"Refreshed {rel_path}")
    except OSError as exc:
        console.err(f"Failed to refresh managed configs: {exc}")
        return 1

    return 0
