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


def render(template: str, *, project_name: str) -> str:
    return template.replace("__FORGEPY_PROJECT_NAME__", project_name)
