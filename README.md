<br />
<div align="center">
  <a href="https://github.com/Apollogeddon/forgepy">
    <img src="docs/docs/assets/forgepy.svg" alt="Logo" width="100" height="100">
  </a>

  <h3 align="center">Forge.py</h3>

  <p align="center">
    DevOps Support and Quality Control for modern Python projects
    <br />
    <a href="https://apollogeddon.github.io/forgepy/"><strong>Explore the docs</strong></a>
    <br />
    <br />
    <a href="https://apollogeddon.github.io/forgepy/getting-started/">Getting Started</a>
    &middot;
    <a href="https://apollogeddon.github.io/forgepy/configuration/">Configuration</a>
    &middot;
    <a href="https://apollogeddon.github.io/forgepy/workflows/overview/">Workflows</a>
  </p>
</div>

<br />

## Installation

Install the tool with uv:

```bash
uv tool install forgepy
```

Or run it once without installing:

```bash
uvx forgepy init
```

## Getting Started

To quickly set up your project with the recommended configurations, tasks, and CI workflows, use the `init` command.

```bash
forgepy init [options]
```

By default, this sets up a **Python Backend/Service**. You can specify other modes:

* `--backend` (Default) for Python services and applications.
* `--library` for publishable PyPI packages.
* `--website` for static documentation sites (Zensical).

This command will:

* **Scaffold Configs:** Create `ruff.toml`, `pyrightconfig.json`, `pytest.toml`, `.pre-commit-config.yaml`, and others depending on the mode (e.g., `Dockerfile`, `nfpm.yaml`, or `mkdocs.yml`).
* **Inject Tasks:** Add `lint`, `type`, `test`, and `build` to `[tool.poe.tasks]` in your `pyproject.toml`.
* **Standardise:** Create a starter package so `uv sync` and the generated tooling work immediately, and leave existing files alone unless you pass `--force`.

Run `forgepy init --help` for the full flag reference.

## Standardised Stack

Forge.py enforces a standardised stack designed for performance and reliability:

| Category | Tool | Description |
| :--- | :--- | :--- |
| **Linting & Formatting** | [Ruff](https://docs.astral.sh/ruff/) | Extremely fast linter and formatter replacing Flake8, isort, and Black. |
| **Type Checking** | [basedpyright](https://docs.basedpyright.com/) | Strict-mode type checker built on Pyright. |
| **Security Scanning** | [Gitleaks](https://github.com/gitleaks/gitleaks) + [OSV-Scanner](https://osv.dev/) | Secret detection and Google's vulnerability scanner for dependencies. |
| **Testing** | [pytest](https://docs.pytest.org/) | Mature testing framework with coverage reporting. |
| **Task Running** | [poethepoet](https://poethepoet.natn.io/) | Runs the project's tasks straight from `pyproject.toml`. |
| **Git Hooks** | [pre-commit](https://pre-commit.com/) | Multi-language Git hooks manager. |
| **Commits** | [commitizen](https://commitizen-tools.github.io/commitizen/) | Enforces Conventional Commits standards. |
| **Releases** | [Release Please](https://github.com/googleapis/release-please) | Automated versioning and changelogs via GitHub Actions. |
| **CI/CD** | [GitHub Actions](https://github.com/features/actions) | Reusable workflows for Testing, Quality, and Releases. |
| **Containers** | [Docker Buildx](https://docs.docker.com/build/) | With `--docker`, CI builds the image for `linux/amd64` and `linux/arm64` (configurable via the `docker` job's `platforms` input) on every PR and pushes it to GHCR on release. |

## Tooling & Versioning Strategy

Forge.py takes an opinionated, batteries-included approach to tooling.

* **Managed Versions:** This package manages the versions of core tools (Ruff, basedpyright, pytest, ...) as dependencies.
* **Simplified Upgrades:** To upgrade your linter or test runner, simply upgrade `forgepy`, then run `forgepy sync` to refresh the vendored configs in `.forgepy/` (`forgepy sync --check` reports drift without writing, and is already wired into the generated pre-commit hook and CI).
* **Security First:** Security scanning is integrated into the standard workflow to catch vulnerabilities early.
* **Stability:** Every mode is verified end-to-end (`uv sync` plus the full generated task list) before a new version is released.
