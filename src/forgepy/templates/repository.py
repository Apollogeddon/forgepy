from __future__ import annotations

from dataclasses import dataclass

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


# The packages published alongside forgepy: proposed daily, in a group of their own, and
# with no cooldown, as their releases aren't a third party's.
OWN_PACKAGES = "forgepy"


@dataclass(frozen=True)
class _Ecosystem:
    name: str
    prefix: str
    group: str
    # only these update types are grouped; others get a pull request each
    update_types: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    own: str = ""


def _ecosystem(e: _Ecosystem) -> str:
    lines = [
        f'  - package-ecosystem: "{e.name}"',
        '    directory: "/"',
        "    schedule:",
        f'      interval: "{"daily" if e.own else "weekly"}"',
        "    groups:",
    ]
    if e.own:
        lines += ["      apollogeddon:", "        patterns:", f'          - "{e.own}"']
    lines += [f"      {e.group}:", "        patterns:", '          - "*"']
    if e.update_types:
        lines += ["        update-types:", *(f'          - "{t}"' for t in e.update_types)]
    lines += ["    commit-message:", f'      prefix: "{e.prefix}"']
    if e.ignore:
        lines += ["    ignore:", *(f'      - dependency-name: "{d}"' for d in e.ignore)]
    lines += ["    cooldown:", "      default-days: 3"]
    if e.own:
        lines += ["      exclude:", f'        - "{e.own}"']
    return "\n".join(lines)


def dependabot(*, docker: bool) -> str:
    ecosystems = [
        _ecosystem(_Ecosystem("uv", "fix(deps)", "dependencies", ("minor", "patch"), own=OWN_PACKAGES)),
        # the reusable workflows are called at @main, which has no versions to propose
        _ecosystem(_Ecosystem("github-actions", "chore(ci)", "actions", ignore=("apollogeddon/forgepy",))),
    ]
    if docker:
        ecosystems.append(_ecosystem(_Ecosystem("docker", "fix(deps)", "docker", ("minor", "patch"))))
    return (
        "version: 2\n"
        "# Every update waits 3 days after a version is published before it's proposed, so a\n"
        "# compromised release has time to be caught and yanked upstream first; our own packages\n"
        "# don't wait, as we published them.\n"
        "updates:\n" + "\n\n".join(ecosystems) + "\n"
    )
