from __future__ import annotations

MKDOCS_YML = """\
site_name: __FORGEPY_PROJECT_NAME__
theme:
  name: material
  variant: classic
docs_dir: docs
site_dir: dist
nav:
  - Home: index.md
"""

DOCS_INDEX_MD = """\
# __FORGEPY_PROJECT_NAME__

Welcome to the documentation site.
"""


def render(template: str, *, project_name: str) -> str:
    return template.replace("__FORGEPY_PROJECT_NAME__", project_name)
