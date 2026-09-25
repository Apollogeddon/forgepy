from __future__ import annotations

# Plain (non f-string) templates — see workflows.py for why.

DOCKERFILE_BACKEND = """\
FROM ghcr.io/astral-sh/uv:python__FORGEPY_PYTHON_VERSION__-bookworm-slim AS build
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY . .
RUN uv sync --locked --no-dev

FROM python:__FORGEPY_PYTHON_VERSION__-slim-bookworm
WORKDIR /app
COPY --from=build /app /app
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "__FORGEPY_PACKAGE_NAME__"]
"""

DOCKERFILE_WEBSITE = """\
FROM ghcr.io/astral-sh/uv:python__FORGEPY_PYTHON_VERSION__-bookworm-slim AS build
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY . .
RUN uv run mkdocs build -d dist

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
