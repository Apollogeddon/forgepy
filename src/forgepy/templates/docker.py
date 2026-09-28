from __future__ import annotations

# Plain (non f-string) templates — see workflows.py for why.

# The venv holds platform-specific wheels, so it's built per target platform. uv comes from pip
# because the ghcr.io/astral-sh/uv images only ship linux/amd64 and linux/arm64, while uv's wheels
# cover every platform python:slim does. `--frozen` because CI already enforces the lockfile, and it
# lets uv skip dev-only sources (like forgepy) the build context can't reach.
DOCKERFILE_BACKEND = """\
# syntax=docker/dockerfile:1
FROM python:__FORGEPY_PYTHON_VERSION__-slim-bookworm AS build
RUN pip install --no-cache-dir uv==0.12.19
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY . .
RUN uv sync --frozen --no-dev

FROM python:__FORGEPY_PYTHON_VERSION__-slim-bookworm
WORKDIR /app
COPY --from=build /app /app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "__FORGEPY_PACKAGE_NAME__"]
"""

# The static site is platform-independent, so it's built once on the build host and only the nginx
# runtime is per target platform. mkdocs is a dev dependency, so the dev group is installed minus
# forgepy itself, which the build doesn't need; `uv run --no-sync` stops uv re-adding it.
DOCKERFILE_WEBSITE = """\
# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM ghcr.io/astral-sh/uv:python__FORGEPY_PYTHON_VERSION__-bookworm-slim AS build
ENV UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-install-package forgepy
COPY . .
RUN uv run --no-sync mkdocs build -d dist

FROM nginx:stable-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""

DOCKERIGNORE = """\
.venv
dist
.git
.github
__pycache__
.pytest_cache
.ruff_cache
htmlcov
"""


def render(template: str, *, python_version: str, package_name: str = "") -> str:
    return template.replace("__FORGEPY_PYTHON_VERSION__", python_version).replace(
        "__FORGEPY_PACKAGE_NAME__", package_name
    )
