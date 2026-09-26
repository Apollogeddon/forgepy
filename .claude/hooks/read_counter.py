"""PreToolUse hook (Read|Grep): counts calls per session, nudges toward
spawning a Haiku Explore agent past the threshold set in CLAUDE.md.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

WARNING_THRESHOLD = 3
WARNING_INTERVAL = 5


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
            f"Read/Grep call #{count} this session — CLAUDE.md says to delegate "
            "multi-file exploration to a Haiku Explore agent instead of reading directly."
        )
        sys.stdout.write(json.dumps({"systemMessage": message}))


if __name__ == "__main__":
    main()
