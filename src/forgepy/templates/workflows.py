from __future__ import annotations

import re

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


DOCKER_JOB = """
  docker:
    needs: __FORGEPY_PIPELINE__
    uses: apollogeddon/forgepy/.github/workflows/docker.yml@main
    permissions:
      contents: read
      packages: write
    with:
      push: ${{ github.ref == 'refs/heads/main' && needs.__FORGEPY_PIPELINE__.outputs.new_release_published == 'true' }}
      version: ${{ needs.__FORGEPY_PIPELINE__.outputs.version }}
    secrets: inherit
"""


def render(template: str, *, python_version: str, docker: bool = False) -> str:
    rendered = template.replace("__FORGEPY_PYTHON_VERSION__", python_version)
    if docker:
        # Docker is a separate job rather than part of the shared pipelines so projects without it
        # don't carry a permanently skipped job; it runs after the pipeline and pushes on release.
        match = re.search(r"^jobs:\n {2}([\w-]+):", rendered, re.MULTILINE)
        if match is None:
            msg = "workflow template has no pipeline job"
            raise ValueError(msg)
        rendered += DOCKER_JOB.replace("__FORGEPY_PIPELINE__", match.group(1))
    return rendered
