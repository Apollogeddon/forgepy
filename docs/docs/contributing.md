---
title: Contributing
description: Quality control tools and commit conventions for contributing to Forge.py.
---

# Contributing

This repository uses a strict set of tools to ensure code quality and a standard development experience — the same toolchain Forge.py scaffolds into other projects.

## Development Setup

```bash
git clone https://github.com/Apollogeddon/forgepy
cd forgepy
uv sync
uv run poe hooks
```

## Quality Control Tools

| Task | What it runs |
| :--- | :--- |
| `uv run poe lint` | Ruff lint with fixes, then Ruff format |
| `uv run poe type` | basedpyright in strict mode |
| `uv run poe test` | The full pytest suite, including the slow end-to-end tests |
| `uv run poe test:unit` | Unit tests only — quiet, no coverage, skips the slow tests |
| `uv run poe security` | OSV-Scanner over the dependency tree |

Run `lint`, `type` and `test` before opening a pull request.

> **Note**
> The slow tests (marked `slow`) scaffold real projects, run `uv sync`, and execute every generated task. They are the only tests that catch wiring bugs such as a missing dependency, so run the full `poe test` for changes to templates, dependencies or the vendored configs.

## Documentation

This site lives in `docs/` as its own uv project, scaffolded with `forgepy init --website`:

```bash
cd docs
uv sync
uv run poe dev     # live preview at http://127.0.0.1:8000/forgepy/
```

## Conventional Commits

The project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification, enforced by commitizen. This format is required for the automated release pipeline to work.

### Commit Types

1. **Features** (`feat`) — Triggers a **minor** release.
   Example: `feat: add docker support for website mode`

2. **Fixes** (`fix`) — Triggers a **patch** release.
   Example: `fix: include tests in pyrightconfig only when present`

3. **Maintenance** (`chore`) — Does **not** trigger a release.
   Example: `chore: update readme`

> **Breaking Changes**
> Include `BREAKING CHANGE:` in the footer or a `!` after the type/scope (e.g., `feat!: rename the sync command`) to trigger a **major** release.
