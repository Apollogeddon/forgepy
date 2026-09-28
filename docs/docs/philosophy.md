---
title: Philosophy & Stack
description: Why Forge.py prioritises fast tools and centralised configuration.
---

# Philosophy & Stack

Forge.py implements an opinionated toolchain designed to prioritise execution speed and configuration simplicity.

## High-Performance Tooling

The project prioritises tools written in compiled languages over pure Python implementations to minimise CI execution time and local feedback loops.

- **Ruff:** Written in Rust, Ruff combines linting, import sorting and formatting in a single pass. It replaces Flake8, isort, Black and a long tail of plugins with one dependency.
- **uv:** Written in Rust, uv resolves, installs and locks dependencies an order of magnitude faster than pip, and manages virtual environments and Python versions in the same tool.
- **basedpyright:** A strict-by-default fork of Pyright with extra checks, run as a single binary with no configuration beyond the managed base.

## Standardisation as a Service

Forge.py abstracts configuration to prevent "drift" across repositories. Improvements to the toolchain reach every project through a single dependency upgrade.

- **Managed versions:** Tool versions ship as Forge.py's `toolchain` extra, so upgrading Forge.py upgrades Ruff, basedpyright, pytest and friends together.
- **Vendored base configs:** `forgepy sync` refreshes the shared Ruff and basedpyright configs in `.forgepy/`, and `forgepy sync --check` catches a stale snapshot in pre-commit and CI.
- **release-please:** Automates the release lifecycle. Version numbers and changelogs are derived from commit history, removing manual intervention from releases.
- **Centralised CI/CD:** Reusable GitHub Actions workflows give every project the same security audits, quality gates and deployment patterns.
- **Verified end to end:** Every mode is scaffolded, synced with uv and run through its full generated task list before a new version is released.

## The Toolchain

| Tool | Why? | Replaces |
| :--- | :--- | :--- |
| **Ruff** | One fast tool for linting, import sorting and formatting. | Flake8, isort, Black |
| **basedpyright** | Strict type checking with better defaults. | mypy, plain Pyright |
| **uv** | Fast, lockfile-based dependency and environment management. | pip, venv, Poetry |
| **pytest** | Fixtures, plugins and coverage with minimal boilerplate. | unittest, nose |
| **poethepoet** | Project tasks defined in `pyproject.toml`. | Makefiles, ad-hoc scripts |
| **pre-commit** | Runs the same checks locally that CI runs. | Manual pre-commit checks |
| **commitizen** | Enforces a structured commit history for automation. | Manual review of commit messages |
| **release-please** | Deterministic versioning and changelog generation. | Manual tagging, manual changelogs |
| **nfpm** | Native Debian packaging without Debian tooling. | dh-virtualenv |
