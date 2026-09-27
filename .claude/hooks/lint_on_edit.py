"""PostToolUse hook (Edit|Write): runs ruff check --fix + ruff format on the touched file.

Unfixable diagnostics exit 2 so they're fed back to Claude (plain stdout only reaches the transcript).
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
        check = subprocess.run(  # noqa: S603
            ["uv", "run", "--no-sync", "ruff", "check", "--fix", file],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
        subprocess.run(["uv", "run", "--no-sync", "ruff", "format", file], capture_output=True, check=False)  # noqa: S603, S607
    except OSError as err:
        sys.stderr.write(f"lint hook could not run ruff: {err}")
        sys.exit(2)

    if check.returncode != 0:
        sys.stderr.write(check.stdout + check.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
