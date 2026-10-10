---
title: Getting started
description: Install Forge.py and scaffold a project with forgepy init.
---

# Getting started

This page shows you how to install Forge.py, scaffold a project with `forgepy init`, and which tasks and flags it provides.

## Requirements

- [uv](https://docs.astral.sh/uv/). Forge.py generates uv-managed projects, and every task runs through `uv run`.
- Python 3.13, or the version you pass to `--python`. uv can install it for you.
- Git, for the pre-commit hooks.

Some optional tasks call tools that uv doesn't install. Put them on your `PATH` if you use those tasks:

| Tool | Needed by |
| :--- | :--- |
| [OSV-Scanner](https://google.github.io/osv-scanner/) | The `security` task |
| [Docker](https://docs.docker.com/get-docker/) | The `docker-build` and `docker-run` tasks (`--docker`) |
| [nFPM](https://nfpm.goreleaser.com/) | The `build-deb` task (`--debian`) |

CI installs these tools itself.

## Install

Forge.py isn't published to PyPI. Install it from GitHub as a uv tool:

```bash
uv tool install git+https://github.com/apollogeddon/forgepy
```

Or run it once without installing:

```bash
uvx --from git+https://github.com/apollogeddon/forgepy forgepy init
```

## Scaffold a project

Run `init` in an existing project, or in an empty directory to start a new one:

```bash
forgepy init            # Python service or application (default)
forgepy init --library  # package published to PyPI
forgepy init --website  # static documentation site (Zensical)
```

Then install the toolchain and the Git hooks:

```bash
uv sync
uv run poe hooks
```

The generated `pyproject.toml` adds `forgepy[toolchain]` to the `dev` dependency group and points `[tool.uv.sources]` at the Forge.py Git repository, so `uv sync` installs Forge.py and its tools into the project's virtual environment.

`init` is safe to re-run. It creates missing files and tasks, and leaves anything that already exists alone.

### Overwrite existing files

Pass `--force` to replace existing config files and tasks with the Forge.py defaults:

```bash
forgepy init --dry-run --force   # preview
forgepy init --force
```

`--force` never touches your own source code: the starter `src/<package>/__init__.py`, `__main__.py` and `tests/test_placeholder.py` are only created when missing. With `--force`, `init` also deletes the files of a feature you have turned off, such as `pytest.toml` after `--no-testing`.

## Tasks

Forge.py adds [Poe the Poet](https://poethepoet.natn.io/) tasks to `[tool.poe.tasks]` in `pyproject.toml`. Run them with `uv run poe <task>`.

| Task | Command | Added when |
| :--- | :--- | :--- |
| `lint` | `ruff check --fix . && ruff format .` | Linting on |
| `format` | `ruff format .` | Linting on |
| `type` | `basedpyright` | Always |
| `security` | `osv-scanner scan -r .` | Linting on |
| `hooks` | `pre-commit install` | Linting on |
| `sync-check` | `forgepy sync --check` | Linting on |
| `compat` | `vermin --target=2.7- ... src && forgepy check-jython src`, which fails on syntax or modules Jython 2.7 lacks | `--jython` |
| `test` | `pytest` | Testing on |
| `build` | `uv build` (`zensical build` for websites) | Not `--jython` |
| `start` | `python -m <package>` | `--backend`, not `--jython` |
| `watch` | `watchmedo auto-restart -- python -m <package>` | `--backend`, not `--jython` |
| `check-dist` | `validate-pyproject pyproject.toml` | `--library` |
| `dev` | `zensical serve` | `--website` |
| `docker-build`, `docker-run` | `docker build` and `docker run` for the project image | `--docker` |
| `build-deb` | Builds a relocatable virtual environment and packages it with nFPM | `--debian` |

An existing task with the same name is kept unless you pass `--force`.

## CLI options

```text
forgepy init [options]
forgepy sync [--check] [-C DIR]
forgepy check-jython PATH...
forgepy --version
```

### `forgepy init`

| Option | Description |
| :--- | :--- |
| `--backend` | Python service or application (default). |
| `--library` | Package published to PyPI. |
| `--website` | Static documentation site built with [Zensical](https://zensical.org/). This is a docs site, not a frontend application mode. |
| `--testing`, `--no-testing` | pytest and coverage (default: on). |
| `--linting`, `--no-linting` | Ruff, basedpyright and pre-commit (default: on). |
| `--versioning`, `--no-versioning` | release-please and Commitizen (default: on). |
| `--all`, `--no-all` | Turn every standard feature on or off at once. An explicit flag such as `--testing` still wins. |
| `--docker` | Add a `Dockerfile` and a container CI job. Not available with `--library`. |
| `--debian` | Add nFPM-based `.deb` packaging. `--backend` only. |
| `--jython` | Scripts that run on Jython 2.7: no packaging, lint rules that keep Python 2 syntax, and a vermin compatibility check. `--backend` only; needs linting, and can't be combined with `--docker` or `--debian`. See [Jython projects](configuration.md#jython-projects). |
| `--force` | Overwrite existing config files and tasks, and remove the files of features you turned off. |
| `--dry-run` | Show what would change without writing anything. |
| `--python VERSION` | Target Python version (default: `3.13`). |
| `-C DIR`, `--path DIR` | Target directory (default: the current directory). |

`--website` scaffolds a static documentation site built with Zensical: `mkdocs.yml`, which Zensical reads as its configuration, and `docs/index.md`. There is no Python package. `uv run poe dev` serves the site locally with live reload, and `uv run poe build` writes it to `dist/`. In CI, the `website.yml` workflow builds the site and deploys `dist/` to GitHub Pages.

`--no-testing` and `--no-versioning` also turn off the matching jobs in the generated CI workflow.

### `forgepy sync`

Refreshes the managed base configs under `.forgepy/` from the installed version of Forge.py. `--check` reports drift without writing anything and exits with status `1` if any file is out of date. `-C DIR` sets the project directory. See [Managed configs](configuration.md#managed-configs).

### `forgepy check-jython`

Reports a comma after `*args` or `**kwargs`, which Ruff's formatter can add and Jython 2.7 rejects. It is the part of a `--jython` project's `compat` task that vermin can't do. See [Jython projects](configuration.md#jython-projects).

## Project structure

A default `forgepy init` (backend) produces:

```text
.
├── .forgepy/
│   ├── pyrightconfig.json      # managed base config, refreshed by `forgepy sync`
│   └── ruff.toml               # managed base config, refreshed by `forgepy sync`
├── .github/
│   ├── .release.json           # release-please manifest
│   ├── CODEOWNERS              # requests your review on others' pull requests
│   ├── dependabot.yml          # weekly updates with a 3-day cooldown
│   ├── release.json            # release-please config
│   └── workflows/index.yml     # CI/CD calling the reusable workflows
├── src/<package>/
│   ├── __init__.py
│   └── __main__.py
├── tests/test_placeholder.py
├── .editorconfig
├── .pre-commit-config.yaml
├── .python-version
├── pyproject.toml              # build system, poe tasks, dev dependencies
├── pyrightconfig.json          # extends .forgepy/pyrightconfig.json
├── pytest.toml
└── ruff.toml                   # extends .forgepy/ruff.toml
```

Other modes and features change this layout:

- `--library` omits `__main__.py`.
- `--website` replaces `src/` with `mkdocs.yml` and `docs/index.md`.
- `--docker` adds `Dockerfile` and `.dockerignore`.
- `--debian` adds `nfpm.yaml` and a `packaging/` directory.
- `--jython` replaces `src/<package>/` with a starter `src/hello.py` and adds `.forgepy/ruff-jython.toml`.
