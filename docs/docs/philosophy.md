---
title: Philosophy and stack
description: Why Forge.py picks fast tools and keeps their configuration in one place.
---

# Philosophy and stack

Forge.py is opinionated: it picks one tool for each job and one shared configuration for each tool. This page explains those choices.

## Fast feedback

Forge.py favours tools that keep local checks and CI runs short.

- **Ruff** is written in Rust and does linting, import sorting and formatting in one tool. It replaces Flake8, isort, Black and many Flake8 plugins.
- **uv** is written in Rust. It resolves, installs and locks dependencies much faster than pip, and also manages virtual environments and Python versions.
- **basedpyright** is a fork of Pyright with stricter defaults and extra checks. It installs from PyPI with its own Node.js runtime, so you don't need Node.js installed.

## One configuration, many projects

Forge.py keeps tool configuration in one place so repositories don't drift apart.

- **Shared tool requirements:** the `forgepy[toolchain]` extra sets the minimum versions of Ruff, basedpyright, pytest and the other tools for every project that uses it.
- **Vendored base configs:** `forgepy sync` refreshes the shared Ruff and basedpyright configs in `.forgepy/`, and `forgepy sync --check` catches a stale copy in pre-commit and CI.
- **Automated releases:** release-please derives version numbers and changelogs from Conventional Commits, so nobody tags releases by hand.
- **Reusable CI:** every project calls the same reusable GitHub Actions workflows, so they share the same security scans, quality gates and delivery steps.
- **Tested end to end:** Forge.py's own test suite scaffolds each mode, runs `uv sync` and runs every generated task. CI runs it before each release.

## The toolchain

| Tool | Why | Replaces |
| :--- | :--- | :--- |
| Ruff | One fast tool for linting, import sorting and formatting | Flake8, isort, Black |
| basedpyright | Strict type checking with better defaults | mypy, Pyright |
| uv | Fast, lockfile-based dependency and environment management | pip, venv, Poetry |
| pytest | Fixtures, plugins and coverage with little boilerplate | unittest, nose |
| Poe the Poet | Project tasks defined in `pyproject.toml` | Makefiles, ad hoc scripts |
| pre-commit | Runs the same checks locally that CI runs | Manual checks before committing |
| Commitizen | Enforces Conventional Commits, which release automation relies on | Manual review of commit messages |
| release-please | Versioning and changelogs from commit history | Manual tagging and changelogs |
| nFPM | Builds `.deb` packages without Debian packaging tools | dh-virtualenv |
