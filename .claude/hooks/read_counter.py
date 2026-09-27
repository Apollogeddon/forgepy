"""PostToolUse hook (Read|Grep|Glob): past a threshold, nudges Claude toward an Explore agent.

Uses additionalContext because a plain systemMessage only reaches the user, never the model.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

WARNING_THRESHOLD = 10
WARNING_INTERVAL = 8


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return

    session_id = data.get("session_id", "default")
    count_file = Path(tempfile.gettempdir()) / f"claude-forgepy-readcount-{session_id}"

    try:
        count = int(count_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        count = 0
    count += 1
    count_file.write_text(str(count), encoding="utf-8")

    first_warning = count == WARNING_THRESHOLD
    repeat_warning = count > WARNING_THRESHOLD and (count - WARNING_THRESHOLD) % WARNING_INTERVAL == 0
    if first_warning or repeat_warning:
        message = (
            f"Read/Grep/Glob call #{count} this session. If you are still searching rather than "
            "working on files you will edit, delegate the rest of the search to an Explore agent."
        )
        output = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": message}}
        sys.stdout.write(json.dumps(output))


if __name__ == "__main__":
    main()
