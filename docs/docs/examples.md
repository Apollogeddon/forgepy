---
title: Examples
description: Common configuration patterns and workflow recipes for Forge.py projects.
---

# Examples

## Configuration Patterns

### Ignoring Files in Ruff

Add exclusions to your project's `ruff.toml`, below the `extend` line:

```toml
extend = ".forgepy/ruff.toml"
target-version = "py313"
extend-exclude = ["migrations", "scripts/legacy"]

[lint.per-file-ignores]
"tests/**" = ["S101", "S603", "S607"]
"scripts/**" = ["S603", "S607"]
```

Use `extend-exclude` rather than `exclude` so the base config's exclusions still apply.

### Enforcing Coverage Thresholds

Add `--cov-fail-under` to `addopts` in `pytest.toml` to fail the run when coverage drops:

```toml
[pytest]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-branch",
    "--cov-fail-under=90",
    # ...the remaining generated options
]
```

### Relaxing a basedpyright Check

Override individual rules in your `pyrightconfig.json`; the managed base stays in strict mode for everything else:

```json
{
  "extends": ".forgepy/pyrightconfig.json",
  "include": ["src", "tests"],
  "venvPath": ".",
  "venv": ".venv",
  "reportMissingTypeStubs": "warning"
}
```

### Adding Your Own Tasks

Add tasks alongside the generated ones in `pyproject.toml`. Forge.py never removes tasks it didn't create:

```toml
[tool.poe.tasks]
migrate = "alembic upgrade head"
check = ["lint", "type", "test"]   # runs the three in sequence
```

## Workflow Patterns

### Monorepo Execution

Point a workflow at a sub-directory with `working_directory`:

```yaml
jobs:
  api:
    uses: apollogeddon/forgepy/.github/workflows/service.yml@main
    permissions:
      contents: write
      pull-requests: write
    with:
      working_directory: 'services/api'
      python_version: '3.13'
```

### Testing Across Python Versions

Call `testing.yml` from a matrix to run the quality and test jobs on several interpreters:

```yaml
jobs:
  test:
    strategy:
      matrix:
        python: ['3.12', '3.13']
    uses: apollogeddon/forgepy/.github/workflows/testing.yml@main
    with:
      python_version: ${{ matrix.python }}
      # artifact names must be unique per run
      artifact_name: dist-py${{ matrix.python }}
```

### Custom Build Steps

`testing.yml` runs `uv build` by default; pass `build_command` to change it. The website workflow uses this to build the site with Zensical:

```yaml
jobs:
  website:
    uses: apollogeddon/forgepy/.github/workflows/website.yml@main
    with:
      build_command: 'uv run zensical build --strict'
```

### Building Docker Images for More Platforms

With `--docker`, CI builds `linux/amd64` and `linux/arm64`. Add platforms with the `docker` job's `platforms` input:

```yaml
jobs:
  docker:
    needs: service
    uses: apollogeddon/forgepy/.github/workflows/docker.yml@main
    permissions:
      contents: read
      packages: write
    with:
      push: ${{ github.ref == 'refs/heads/main' && needs.service.outputs.new_release_published == 'true' }}
      version: ${{ needs.service.outputs.version }}
      platforms: 'linux/amd64,linux/arm64,linux/arm/v7'
```
