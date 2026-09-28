from __future__ import annotations

# Plain templates: GitHub Actions "${{ ... }}" collides with f-string/Template syntax,
# so substitution uses str.replace() on __FORGEPY_*__ tokens instead.

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
      pages: write
      id-token: write
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


def render(template: str, *, python_version: str, docker: bool = False) -> str:
    rendered = template.replace("__FORGEPY_PYTHON_VERSION__", python_version)
    if docker:
        # Docker is an add-on to any non-library pipeline, so it's layered onto the mode's template.
        # packages: write lets the reusable docker.yml push to GHCR with the caller's token.
        permission = "      pull-requests: write\n"
        rendered = rendered.replace(permission, permission + "      packages: write\n", 1)
        rendered = rendered.replace("    with:\n", "    with:\n      docker: true\n", 1)
    return rendered
