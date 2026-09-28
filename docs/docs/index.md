---
title: Quality tooling, zero configuration drift
hide:
  - navigation
  - toc
---

<div class="fp-hero" markdown>

<span class="fp-badge">Python 3.13 · uv · forgepy</span>

# Quality tooling,<br>zero configuration drift.

<p>Reusable GitHub Actions workflows and tooling configurations for modern Python projects. Centralise your ruff, basedpyright and pytest setup and scaffold projects with a single command.</p>

[Get Started :material-arrow-right:](getting-started.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/Apollogeddon/forgepy){ .md-button }

</div>

## Why Forge.py { .fp-section-title }

<div class="grid cards fp-cols-2" markdown>

-   :material-tune-variant:{ .lg .middle .fp-icon } __Standardised Tooling__

    ---

    Default configurations for Ruff, basedpyright and pytest enforce consistency across every project from day one.

-   :material-source-branch-sync:{ .lg .middle .fp-icon } __Reusable Workflows__

    ---

    Modular GitHub Actions workflows for testing, building, and releasing — no manual YAML authoring required.

-   :material-folder-plus-outline:{ .lg .middle .fp-icon } __Project Scaffolding__

    ---

    Bootstrap a complete repository instantly with a single `forgepy init`. No boilerplate to copy-paste.

-   :material-tag-arrow-up-outline:{ .lg .middle .fp-icon } __Automated Releases__

    ---

    release-please pipelines handle versioning, changelogs, and publishing deterministically from commit history.

</div>

## Quick Start { .fp-section-title }

<div class="grid cards" markdown>

-   __01 · Install__

    ---

    Install Forge.py as a uv tool.

    ```bash
    uv tool install forgepy
    ```

-   __02 · Initialise__

    ---

    Run the CLI to scaffold configs and inject standard tasks.

    ```bash
    forgepy init
    ```

-   __03 · Extend__

    ---

    Inherit best practices by extending the vendored ruff config.

    ```toml
    # ruff.toml
    extend = ".forgepy/ruff.toml"
    ```

</div>

## The Toolchain { .fp-section-title }

<div class="grid cards fp-cols-4" markdown>

-   __Ruff__ · Rust

    ---

    Replaces Flake8, isort, Black

-   __basedpyright__ · TS/Node

    ---

    Replaces mypy, plain pyright

-   __uv__ · Rust

    ---

    Replaces pip, venv, Poetry

-   __pytest__ · Python

    ---

    Replaces unittest, nose

-   __poethepoet__ · Python

    ---

    Replaces Makefiles, ad-hoc scripts

-   __pre-commit__ · Python

    ---

    Replaces manual pre-commit checks

-   __commitizen__ · Python

    ---

    Replaces manual commit review

-   __release-please__ · GitHub Action

    ---

    Replaces manual tagging and changelogs

</div>
