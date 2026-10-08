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

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  # never cancel a run on main mid-release, or the release is created but never published
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}

jobs:
  library:
    uses: apollogeddon/forgepy/.github/workflows/library.yml@main
    permissions:
      contents: write
      pull-requests: write
      # PyPI trusted publishing (OIDC)
      id-token: write
    with:
      python_version: '__FORGEPY_PYTHON_VERSION__'
"""

SERVICE_WORKFLOW = """\
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  # never cancel a run on main mid-release, or the release is created but never published
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}

jobs:
  service:
    uses: apollogeddon/forgepy/.github/workflows/service.yml@main
    permissions:
      contents: write
      pull-requests: write
    with:
      python_version: '__FORGEPY_PYTHON_VERSION__'
"""


WEBSITE_WORKFLOW = """\
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  # never cancel a run on main mid-release, or the release is created but never published
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}

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
"""

DEBIAN_WORKFLOW = """\
name: CI

on:
  push:
    branches: ["main"]
  pull_request:
    branches: ["main"]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  # never cancel a run on main mid-release, or the release is created but never published
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}

jobs:
  debian:
    uses: apollogeddon/forgepy/.github/workflows/debian.yml@main
    permissions:
      contents: write
      pull-requests: write
    with:
      python_version: '__FORGEPY_PYTHON_VERSION__'
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
"""


def render(template: str, *, python_version: str, docker: bool = False, inputs: dict[str, bool] | None = None) -> str:
    rendered = template.replace("__FORGEPY_PYTHON_VERSION__", python_version)
    if inputs:
        # Disabled standard features become pipeline inputs so CI doesn't run what the project doesn't have
        lines = "".join(f"      {key}: {str(value).lower()}\n" for key, value in inputs.items())
        rendered = rendered.replace("    with:\n", "    with:\n" + lines, 1)
    if docker:
        # Docker is a separate job rather than part of the shared pipelines so projects without it
        # don't carry a permanently skipped job; it runs after the pipeline and pushes on release.
        match = re.search(r"^jobs:\n {2}([\w-]+):", rendered, re.MULTILINE)
        if match is None:
            msg = "workflow template has no pipeline job"
            raise ValueError(msg)
        rendered += DOCKER_JOB.replace("__FORGEPY_PIPELINE__", match.group(1))
    return rendered
