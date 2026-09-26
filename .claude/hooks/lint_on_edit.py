"""PostToolUse hook (Edit|Write): runs ruff check --fix + ruff format on the
touched file for instant feedback, mirroring the repo's `poe lint` task.
"""

from __future__ import annotations

import json
import subprocess
import sys


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    file = data.get("tool_input", {}).get("file_path") or data.get("tool_response", {}).get("filePath")
    if not file or not file.endswith(".py"):
        return

    try:
        # uv resolved via PATH; file comes from Claude Code's own trusted tool_input, not user input
        subprocess.run(["uv", "run", "ruff", "check", "--fix", file], check=False)  # noqa: S603, S607
        subprocess.run(["uv", "run", "ruff", "format", file], check=False)  # noqa: S603, S607
    except OSError:
        pass  # non-blocking: surface nothing further, ruff already printed the issue


if __name__ == "__main__":
    main()
