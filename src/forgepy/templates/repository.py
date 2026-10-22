from __future__ import annotations

# Plain (non f-string) templates — see workflows.py for why.

# What uv, the generated tasks and the .deb build write; the project's own from then on
GITIGNORE = """\
# Python and uv
__pycache__/
*.py[oc]
.venv/
dist/

# Test and lint output
.pytest_cache/
.ruff_cache/
.coverage
coverage.json
htmlcov/
junit-report.xml

# Debian packages
*.deb
"""

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


def _ecosystem(name: str, prefix: str, group: str, update_types: tuple[str, ...] = ()) -> str:
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
    lines += ["    cooldown:", "      default-days: 3"]
    return "\n".join(lines)


def dependabot(*, docker: bool) -> str:
    ecosystems = [
        _ecosystem("uv", "fix(deps)", "dependencies", ("minor", "patch")),
        # the actions, and the forgepy release tag .index.yml calls the pipelines at
        _ecosystem("github-actions", "chore(ci)", "actions"),
    ]
    if docker:
        ecosystems.append(_ecosystem("docker", "fix(deps)", "docker", ("minor", "patch")))
    return (
        "version: 2\n"
        "# Every update waits 3 days after a version is published before it's proposed, so a\n"
        "# compromised release has time to be caught and yanked upstream first.\n"
        "updates:\n" + "\n\n".join(ecosystems) + "\n"
    )
