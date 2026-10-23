---
title: Examples
description: Common configuration patterns and workflow recipes for Forge.py projects.
---

# Examples

This page collects short recipes for customising a Forge.py project's configs and CI.

## Configuration patterns

### Ignoring files in Ruff

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

### Enforcing coverage thresholds

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

### Relaxing a basedpyright check

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

### Adding your own tasks

Add tasks alongside the generated ones in `pyproject.toml`. Forge.py never removes tasks, and only replaces one of its own names with `--force`:

```toml
[tool.poe.tasks]
migrate = "alembic upgrade head"
check = ["lint", "type", "test"]   # runs the three in sequence
```

## Workflow patterns

### Projects in a subdirectory

Point the pipelines at a subdirectory, for example in a monorepo, with `working_directory`, given relative to the repository root without a leading `./` or trailing `/`. Give each pipeline the same one:

```yaml
jobs:
  version:
    if: ${{ github.event_name != 'pull_request' && github.event_name != 'schedule' }}
    uses: apollogeddon/forgepy/.github/workflows/version.yml@main
    with:
      working_directory: 'services/api'
    permissions:
      contents: write
      pull-requests: write

  service:
    needs: version
    if: ${{ !cancelled() && (github.event_name == 'pull_request' || needs.version.outputs.new_release_published == 'true') }}
    uses: apollogeddon/forgepy/.github/workflows/service.yml@main
    with:
      working_directory: 'services/api'
    permissions:
      contents: read
      pull-requests: write
```

In a repository with several projects, a second call to the same pipeline names itself after its project in brackets, so the run page reads `service (web) / test`:

```yaml
  service-web:
    name: service (web)
    uses: apollogeddon/forgepy/.github/workflows/service.yml@main
    with:
      working_directory: 'services/web'
```

`version.yml` reads the project's own `services/api/.github/release.json` and `.release.json`, but release-please keys a package by its path from the repository root, so change the `"."` key in both to the subdirectory, and give the package a `component` so its tags and release PR don't collide with another project's:

```json
{
  "packages": {
    "services/api": {
      "release-type": "python",
      "component": "api",
      "extra-files": [
        { "type": "toml", "path": "uv.lock", "jsonpath": "$.package[?(@.name.value=='api')].version" }
      ]
    }
  }
}
```

```json
{
  "services/api": "0.1.0"
}
```

release-please then only counts commits under `services/api`, bumps the version in its `pyproject.toml` and `uv.lock`, and tags its releases with the component (`api-vX.Y.Z`), so several projects in one repository are each released on their own.

### Checking against several dependency groups

Call a check pipeline from a matrix to run its stages once per leg, such as scripts type-checked against each version of a platform's API stubs, each in its own uv dependency group. Keep the job's id the pipeline's name and name each leg in brackets, so the run page reads `library (current) / test`:

```yaml
jobs:
  library:
    name: library (${{ matrix.api }})
    strategy:
      matrix:
        include:
          - api: current
            group: stubs-current
          - api: next
            group: stubs-next
    uses: apollogeddon/forgepy/.github/workflows/library.yml@main
    with:
      working_directory: projects
      sync_args: --no-default-groups --group dev --group ${{ matrix.group }}
      # Jython scripts are deployed as they are
      run_build: false
      # artifact names must be unique per run
      artifact_name: projects-${{ matrix.group }}
    permissions:
      contents: read
      pull-requests: write
```

The same shape runs the checks on several interpreters, with `python_version: ${{ matrix.python }}` in place of `sync_args`. Security patches aren't a check: Dependabot security updates propose them as pull requests, once per lockfile rather than once per leg.

### Custom build steps

`library.yml` and `service.yml` run `uv build` by default, and `website.yml` `uv run zensical build`; pass `build_command` to change it. The command writes to `dist/`, which the build stage uploads:

```yaml
jobs:
  website:
    # ...as generated by forgepy init --website
    uses: apollogeddon/forgepy/.github/workflows/website.yml@main
    with:
      build_command: 'uv run zensical build --strict'
```

### Building Docker images for more platforms

With `--docker`, CI builds `linux/amd64` and `linux/arm64`. Add platforms with the `docker` job's `platforms` input:

```yaml
jobs:
  docker:
    needs: [version, service]
    if: ${{ !cancelled() && needs.service.result == 'success' }}
    uses: apollogeddon/forgepy/.github/workflows/docker.yml@main
    with:
      push: ${{ needs.version.outputs.new_release_published == 'true' }}
      version: ${{ needs.version.outputs.version }}
      platforms: 'linux/amd64,linux/arm64,linux/arm/v7'
    permissions:
      contents: read
      packages: write
```
