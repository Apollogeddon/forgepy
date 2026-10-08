---
title: Contributing
description: Set up a development environment for Forge.py, run its checks, and write commit messages.
---

# Contributing

This page is for people who want to change Forge.py itself. The repository uses the same toolchain that Forge.py scaffolds into other projects.

## Development setup

```bash
git clone https://github.com/Apollogeddon/forgepy
cd forgepy
uv sync
uv run poe hooks
```

## Quality checks

| Task | What it runs |
| :--- | :--- |
| `uv run poe lint` | Ruff lint with fixes, then Ruff format |
| `uv run poe type` | basedpyright in strict mode |
| `uv run poe test` | The full pytest suite, including the slow end-to-end tests |
| `uv run poe test:unit` | Unit tests only: quiet, no coverage, skips the slow tests |
| `uv run poe security` | OSV-Scanner over the dependency tree |

Run `lint`, `type` and `test` before opening a pull request.

!!! note
    The slow tests (marked `slow`) scaffold real projects, run `uv sync`, and run every generated task. They are the only tests that catch wiring bugs such as a missing dependency, so run the full `poe test` after changing templates, dependencies or the vendored configs.

## Documentation

This site lives in `docs/` as its own uv project, scaffolded with `forgepy init --website`. Preview it locally:

```bash
cd docs
uv sync
uv run poe dev     # serves a live preview at http://127.0.0.1:8000/forgepy/
```

## Commit messages

Commit messages follow the [Conventional Commits](https://www.conventionalcommits.org/) specification, which Commitizen checks in the `commit-msg` hook. release-please reads them to decide the next version and write the changelog.

### Commit types

- **Features** (`feat`) trigger a minor release.
  For example: `feat: add docker support for website mode`

- **Fixes** (`fix`) trigger a patch release.
  For example: `fix: include tests in pyrightconfig only when present`

- **Maintenance** (`chore`, `ci`, `docs` and similar) doesn't trigger a release.
  For example: `docs: clarify the sync command`

For a breaking change, add a `BREAKING CHANGE:` footer or a `!` after the type or scope, for example `feat!: rename the sync command`. It triggers a major release.
