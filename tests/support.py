from __future__ import annotations

import os
import shutil
from pathlib import Path


def _bash() -> str:
    """The bash step scripts run in: on Windows, Git's own, as a bare "bash" finds System32's WSL launcher."""
    if os.name != "nt":
        return "bash"
    # git.exe sits in Git/cmd, Git/bin or Git/mingw64/bin, and bash.exe in Git/bin
    git = Path(shutil.which("git") or "git").resolve()
    return next((str(p / "bin" / "bash.exe") for p in git.parents if (p / "bin" / "bash.exe").is_file()), "bash")


BASH = _bash()
