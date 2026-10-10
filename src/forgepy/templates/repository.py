from __future__ import annotations

# Plain (non f-string) templates — see workflows.py for why.

EDITORCONFIG = """\
root = true

[*]
indent_style = space
indent_size = 2
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true
max_line_length = 120

[*.py]
indent_size = 4

[*.md]
trim_trailing_whitespace = false
"""

CODEOWNERS = """\
# Every pull request opened by someone else, Dependabot and release-please included,
# requests a review from the owner, so it shows in their review requests.
* @__FORGEPY_OWNER__
"""


def _ecosystem(
    name: str, prefix: str, group: str, update_types: tuple[str, ...] = (), ignore: tuple[str, ...] = ()
) -> str:
    lines = [
        f'  - package-ecosystem: "{name}"',
        '    directory: "/"',
        "    schedule:",
        '      interval: "weekly"',
        "    groups:",
        f"      {group}:",
        "        patterns:",
        '          - "*"',
    ]
    if update_types:
        # only these update types are grouped; others get a pull request each
        lines += ["        update-types:", *(f'          - "{t}"' for t in update_types)]
    lines += ["    commit-message:", f'      prefix: "{prefix}"']
    if ignore:
        lines += ["    ignore:", *(f'      - dependency-name: "{d}"' for d in ignore)]
    lines += ["    cooldown:", "      default-days: 3"]
    return "\n".join(lines)


def dependabot(*, docker: bool) -> str:
    ecosystems = [
        _ecosystem("uv", "fix(deps)", "dependencies", ("minor", "patch")),
        # the reusable workflows are called at @main, which has no versions to propose
        _ecosystem("github-actions", "chore(ci)", "actions", ignore=("apollogeddon/forgepy",)),
    ]
    if docker:
        ecosystems.append(_ecosystem("docker", "fix(deps)", "docker", ("minor", "patch")))
    return (
        "version: 2\n"
        "# Every update waits 3 days after a version is published before it's proposed, so a\n"
        "# compromised release has time to be caught and yanked upstream first.\n"
        "updates:\n" + "\n\n".join(ecosystems) + "\n"
    )
