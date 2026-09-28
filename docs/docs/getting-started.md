---
title: Getting Started
description: Install Forge.py and bootstrap a project with the init CLI.
---

# Getting Started

## Requirements

- [uv](https://docs.astral.sh/uv/) — Forge.py generates uv-managed projects and its tasks run through `uv run`.
- Python 3.13 (or the version you pass to `--python`).
- Git, for the generated pre-commit hooks.

## Setup Guide

### 1. Installation

Install Forge.py as a uv tool:

```bash
uv tool install forgepy
```

Or run it once without installing:

```bash
uvx forgepy init
```

### 2. Initialisation

Run `init` in an existing project, or in an empty directory to start a new one:

```bash
forgepy init            # Python service/application (default)
forgepy init --library  # publishable PyPI package
forgepy init --website  # static documentation site (Zensical)
```

Then install the toolchain and the Git hooks:

```bash
uv sync
uv run poe hooks
```

`init` is safe to re-run. It creates missing files and tasks, and leaves anything that already exists alone.

### 3. Advanced: Overwriting Files

Pass `--force` to overwrite existing config files and tasks with the Forge.py defaults:

```bash
forgepy init --force
```

`--force` never touches your own source code: the starter `src/<package>/__init__.py`, `__main__.py` and `tests/test_placeholder.py` are only ever created when missing. Use `--dry-run` first to see exactly what would change.

## Injected Tasks

Forge.py adds [poethepoet](https://poethepoet.natn.io/) tasks to `[tool.poe.tasks]` in `pyproject.toml`. Run them with `uv run poe <task>`.

| Task | Command | Added when |
| :--- | :--- | :--- |
| `lint` | `ruff check --fix . && ruff format .` | linting on |
| `format` | `ruff format .` | linting on |
| `type` | `basedpyright` | always |
| `security` | `osv-scanner scan -r .` | linting on |
| `hooks` | `pre-commit install` | linting on |
| `sync-check` | `forgepy sync --check` | linting on |
| `test` | `pytest` | testing on |
| `build` | `uv build` (`zensical build` for websites) | always |
| `start` | `python -m <package>` | `--backend` |
| `watch` | `watchmedo auto-restart -- python -m <package>` | `--backend` |
| `check-dist` | `validate-pyproject pyproject.toml` | `--library` |
| `dev` | `zensical serve` | `--website` |
| `docker-build` / `docker-run` | `docker build` / `docker run` for the project image | `--docker` |
| `build-deb` | builds a relocatable venv and packages it with nfpm | `--debian` |

Existing tasks with the same name are kept unless you pass `--force`.

## CLI Options

```text
forgepy init [options]
forgepy sync [--check]
```

| Option | Description |
| :--- | :--- |
| `--backend` | Python service/application (default). |
| `--library` | Publishable PyPI package. |
| `--website` | Static documentation site built with [Zensical](https://zensical.org/). |
| `--testing` / `--no-testing` | pytest + coverage (default: on). |
| `--linting` / `--no-linting` | Ruff + basedpyright + pre-commit (default: on). |
| `--versioning` / `--no-versioning` | release-please + commitizen (default: on). |
| `--all` / `--no-all` | Enable or disable every standard feature at once; an explicit flag such as `--testing` still wins. |
| `--docker` | Add a `Dockerfile` and container CI (not available for `--library`). |
| `--debian` | Add nfpm-based `.deb` packaging (`--backend` only). |
| `--force` | Overwrite existing config files and tasks. |
| `--dry-run` | Show what would change without writing anything. |
| `--python VERSION` | Target Python version (default: `3.13`). |
| `-C DIR`, `--path DIR` | Target directory (default: the current directory). |

`forgepy sync` refreshes the managed base configs under `.forgepy/` — see [Configuration](configuration.md#managed-configs).

## Project Structure

A default `forgepy init` (backend) produces:

```text
.
├── .forgepy/
│   ├── pyrightconfig.json      # managed base config — refreshed by `forgepy sync`
│   └── ruff.toml               # managed base config — refreshed by `forgepy sync`
├── .github/
│   ├── .release.json           # release-please manifest
│   ├── release.json            # release-please config
│   └── workflows/index.yml     # CI/CD calling the reusable workflows
├── src/<package>/
│   ├── __init__.py
│   └── __main__.py
├── tests/test_placeholder.py
├── .pre-commit-config.yaml
├── .python-version
├── pyproject.toml              # build system, poe tasks, dev dependencies
├── pyrightconfig.json          # extends .forgepy/pyrightconfig.json
├── pytest.toml
└── ruff.toml                   # extends .forgepy/ruff.toml
```

`--library` omits `__main__.py`; `--website` replaces `src/` with `mkdocs.yml` and `docs/index.md`. `--docker` adds `Dockerfile` and `.dockerignore`, and `--debian` adds `nfpm.yaml` and a `packaging/` directory.
