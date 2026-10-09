---
title: Quality tooling, zero configuration drift
hide:
  - navigation
  - toc
---

<div class="fp-hero" markdown>

<span class="fp-badge">Python 3.13 · uv · forgepy</span>

# Quality tooling,<br>zero configuration drift.

<p>Forge.py is a command-line tool that scaffolds linting, type checking, testing, releases and GitHub Actions CI into uv-managed Python projects, and keeps their Ruff, basedpyright and pytest setup in one place.</p>

[Get Started :material-arrow-right:](getting-started.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/Apollogeddon/forgepy){ .md-button }

</div>

## Why Forge.py { .fp-section-title }

<div class="grid cards fp-cols-2" markdown>

-   :material-tune-variant:{ .lg .middle .fp-icon } __Shared tool configs__

    ---

    Every project extends the same Ruff and basedpyright base configs, and `forgepy sync` keeps them current.

-   :material-source-branch-sync:{ .lg .middle .fp-icon } __Reusable workflows__

    ---

    GitHub Actions workflows for checks, builds, releases and delivery. `forgepy init` generates the caller for your project.

-   :material-folder-plus-outline:{ .lg .middle .fp-icon } __Project scaffolding__

    ---

    `forgepy init` sets up a backend, library or documentation site, with optional Docker and Debian packaging.

-   :material-tag-arrow-up-outline:{ .lg .middle .fp-icon } __Automated releases__

    ---

    release-please derives versions and changelogs from Conventional Commits, and the pipeline publishes each release.

</div>

## Quick start { .fp-section-title }

<div class="grid cards" markdown>

-   __01 · Install__

    ---

    Forge.py isn't on PyPI. Install it from GitHub as a uv tool.

    ```bash
    uv tool install git+https://github.com/apollogeddon/forgepy
    ```

-   __02 · Scaffold__

    ---

    Run `init` in your project to write the configs, tasks and CI workflow.

    ```bash
    forgepy init
    ```

-   __03 · Set up__

    ---

    Install the toolchain and the Git hooks.

    ```bash
    uv sync
    uv run poe hooks
    ```

</div>

## The toolchain { .fp-section-title }

<div class="grid cards fp-cols-4" markdown>

-   __Ruff__ · Rust

    ---

    Replaces Flake8, isort, Black

-   __basedpyright__ · TS/Node

    ---

    Replaces mypy, Pyright

-   __uv__ · Rust

    ---

    Replaces pip, venv, Poetry

-   __pytest__ · Python

    ---

    Replaces unittest, nose

-   __Poe the Poet__ · Python

    ---

    Replaces Makefiles, ad-hoc scripts

-   __pre-commit__ · Python

    ---

    Replaces manual pre-commit checks

-   __Commitizen__ · Python

    ---

    Replaces manual commit review

-   __release-please__ · GitHub Action

    ---

    Replaces manual tagging and changelogs

</div>
