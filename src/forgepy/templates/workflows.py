from __future__ import annotations

# Plain (non f-string) templates: GitHub Actions "${{ ... }}" syntax collides with
# both f-string and string.Template placeholder syntax, so substitution below uses
# plain str.replace() on explicit __FORGEPY_*__ tokens instead.

LIBRARY_WORKFLOW = """\
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  library:
    uses: apollogeddon/forgepy/.github/workflows/library.yml@main
    permissions:
      contents: write
      pull-requests: write
      id-token: write
    with:
      python_version: '__FORGEPY_PYTHON_VERSION__'
    secrets: inherit
"""

SERVICE_WORKFLOW = """\
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  service:
    uses: apollogeddon/forgepy/.github/workflows/service.yml@main
    permissions:
      contents: write
      pull-requests: write
    with:
      python_version: '__FORGEPY_PYTHON_VERSION__'
    secrets: inherit
"""


WEBSITE_WORKFLOW = """\
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  website:
    uses: apollogeddon/forgepy/.github/workflows/website.yml@main
    permissions:
      contents: write
      pull-requests: write
    with:
      python_version: '__FORGEPY_PYTHON_VERSION__'
    secrets: inherit
"""

DEBIAN_WORKFLOW = """\
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

jobs:
  debian:
    uses: apollogeddon/forgepy/.github/workflows/debian.yml@main
    permissions:
      contents: write
      pull-requests: write
    with:
      python_version: '__FORGEPY_PYTHON_VERSION__'
    secrets: inherit
"""


def render(template: str, *, python_version: str) -> str:
    return template.replace("__FORGEPY_PYTHON_VERSION__", python_version)
