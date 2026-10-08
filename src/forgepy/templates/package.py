from __future__ import annotations

# Plain (non f-string) templates - see workflows.py for why.

INIT_PY = '''\
"""__FORGEPY_PROJECT_NAME__."""

__version__ = "0.1.0"
'''

MAIN_PY = """\
def main() -> None:
    print("Hello from __FORGEPY_PROJECT_NAME__!")


if __name__ == "__main__":
    main()
"""


# A Jython 2.7 script: str.format rather than f-strings, and a type comment that basedpyright
# reads because the project defines MYPY as true; Jython never runs the typing import.
JYTHON_SCRIPT_PY = '''\
"""__FORGEPY_PROJECT_NAME__: scripts that run on Jython 2.7."""

MYPY = False
if MYPY:
    from typing import Optional


def greet(name=None):
    # type: (Optional[str]) -> str
    """Return a greeting for name, or for the world."""
    return "Hello, {}!".format(name or "world")
'''


def render(template: str, *, project_name: str) -> str:
    return template.replace("__FORGEPY_PROJECT_NAME__", project_name)
