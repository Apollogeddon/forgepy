---
title: Migrating to Forge.py
description: Move an existing Python project to Forge.py and remove the tools it replaces.
---

# Migrating to Forge.py

This page is for moving an existing Python project to Forge.py. Forge.py's configs replace those of several common tools, so you remove the old ones to avoid conflicts.

## Migration checklist

### 1. Run init

Preview the changes, then generate the standard configurations:

```bash
forgepy init --dry-run
forgepy init
```

Existing files are left alone. Pass `--force` to replace your current `ruff.toml`, `pyrightconfig.json`, `pytest.toml` and `.pre-commit-config.yaml` with the Forge.py versions; your source code is never overwritten.

### 2. Remove old configs

Remove the configuration of the tools Forge.py replaces:

- **Flake8, isort, Black:** `.flake8`, `.isort.cfg`, and the `[tool.black]`, `[tool.isort]` and `[flake8]` sections of `pyproject.toml`/`setup.cfg`.
- **mypy:** `mypy.ini` and `[tool.mypy]`.
- **pytest in `pyproject.toml` or `pytest.ini`:** move any custom options into the generated `pytest.toml`, then delete `[tool.pytest.ini_options]` so pytest doesn't pick up two configs.

### 3. Update dependencies

Remove the tools Forge.py replaces, then install the `forgepy[toolchain]` dev dependency that `init` added:

```bash
uv remove --dev flake8 isort black mypy
uv sync
```

List only the packages your project depends on: `uv remove` fails on one that isn't there.

### 4. Fix lint and type errors

Ruff's rule set and basedpyright's strict mode are stricter than many existing setups. Let Ruff fix what it can, then work through the rest:

```bash
uv run poe lint
uv run poe type
```

## Tool-specific notes

### Flake8 and Black to Ruff

Ruff handles both linting and formatting and is largely rule-compatible with Flake8 and its popular plugins. Keep project-specific ignores in your `ruff.toml` below the `extend` line rather than in the managed base.

!!! tip
    In a large codebase with many initial errors, add a temporary `[lint.per-file-ignores]` entry for the noisiest paths and remove it as you fix them. CI still checks every other rule on those files.

### mypy to basedpyright

basedpyright runs in strict mode. Existing `# type: ignore` comments still work, but basedpyright warns about ignores that are no longer needed, which helps clean them up.

### Automated releases

Forge.py uses release-please, through the reusable `version.yml` workflow. Remove any existing version-bumping tooling, such as bump2version, and stop editing the changelog by hand: from now on, Conventional Commits drive releases. `init` starts the release-please manifest at `0.1.0`, so if your project already has a version, set it in `.github/.release.json`.
