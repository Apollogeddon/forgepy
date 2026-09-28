---
title: Migrating to Forge.py
description: Remove conflicting tooling and adopt the Forge.py standard configurations.
---

# Migrating to Forge.py

Adopting Forge.py reduces configuration overhead but requires removing conflicting tool configurations.

## Migration Checklist

### 1. Run Initialisation

Preview the changes, then generate the standard configurations:

```bash
forgepy init --dry-run
forgepy init
```

Existing files are left alone. Pass `--force` to replace your current `ruff.toml`, `pyrightconfig.json`, `pytest.toml` and `.pre-commit-config.yaml` with the Forge.py versions; your source code is never overwritten.

### 2. Remove Old Configs

Remove configuration for tools Forge.py replaces to prevent conflicts:

- **Flake8, isort, Black:** `.flake8`, `.isort.cfg`, and the `[tool.black]`, `[tool.isort]` and `[flake8]` sections of `pyproject.toml`/`setup.cfg`.
- **mypy:** `mypy.ini` and `[tool.mypy]`.
- **pytest in `pyproject.toml` or `pytest.ini`:** move any custom options into the generated `pytest.toml`, then delete `[tool.pytest.ini_options]` so pytest doesn't pick up two configs.

### 3. Update Dependencies

Remove the tools that are now managed by Forge.py's `toolchain` extra:

```bash
uv remove --dev flake8 isort black mypy
uv sync
```

### 4. Fix Linting Errors

Ruff's rule set and basedpyright's strict mode are stricter than many existing setups. Let Ruff fix what it can, then work through the rest:

```bash
uv run poe lint
uv run poe type
```

## Tool-Specific Guides

### Flake8/Black to Ruff

Ruff handles both linting and formatting and is largely rule-compatible with Flake8 and its popular plugins. Keep project-specific ignores in your `ruff.toml` below the `extend` line rather than in the managed base.

> **Tip**
> For a large codebase with many initial errors, add a temporary `[lint.per-file-ignores]` entry for the noisiest paths and remove it as you fix them — CI still checks every file.

### mypy to basedpyright

basedpyright runs in strict mode. Existing `# type: ignore` comments still work, but basedpyright warns about ignores that are no longer needed, which helps clean them up.

### Automated Releases

Forge.py uses **release-please** (via the reusable `version.yml` workflow). Remove any existing version-bumping tooling such as bump2version or a hand-maintained changelog process; releases are driven by Conventional Commits from here on.
