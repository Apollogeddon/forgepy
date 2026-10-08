---
title: Configuration
description: Extend Forge.py tool configurations for project-specific overrides.
---

# Configuration

Forge.py uses a layered configuration model: each tool's project-level config extends a base config that Forge.py manages, so you override only what your project needs.

## Managed Configs

The Ruff and basedpyright base configs live in `.forgepy/` inside your project — a vendored snapshot of the configs bundled with the installed version of Forge.py. Pointing at a local copy (rather than a path inside the virtual environment) keeps the `extend` paths stable across platforms and Python versions.

| File | Purpose |
| :--- | :--- |
| `.forgepy/ruff.toml` | Base Ruff rules. **Do not edit** — it is overwritten on refresh. |
| `.forgepy/pyrightconfig.json` | Base basedpyright settings. **Do not edit.** |

After upgrading Forge.py, refresh the snapshot:

```bash
uv run forgepy sync
```

`forgepy sync --check` reports drift without writing anything and exits `1` if the snapshot is out of date. It is already wired into the generated pre-commit hook, the `sync-check` task and the CI quality job, so a stale snapshot can't slip through.

## Quality & Testing

### Ruff — Linting & Formatting

The generated `ruff.toml` extends the managed base:

```toml
extend = ".forgepy/ruff.toml"
target-version = "py313"

[lint.per-file-ignores]
"tests/**" = ["S101", "S603", "S607"]
```

The base enables a broad rule set — `E`, `F`, `W`, `I`, `UP`, `B`, `SIM`, `RUF`, `PL`, `N`, `A`, `C4`, `PTH`, `PERF`, `RET`, `ARG` and `S` (Bandit security checks) — with a 120-character line length and double quotes. Add project-specific settings below the `extend` line; they take precedence over the base.

### basedpyright — Type Checking

The generated `pyrightconfig.json` extends the managed base, which runs in **strict** mode and treats unused imports and variables as errors:

```json
{
  "extends": ".forgepy/pyrightconfig.json",
  "include": ["src", "tests"],
  "venvPath": ".",
  "venv": ".venv"
}
```

`include` only lists directories that exist for your mode — websites have no `src`, and `--no-testing` drops `tests`.

### pytest — Testing

`pytest.toml` enables strict markers and config, branch coverage of `src`, and HTML, JSON and JUnit reports:

```toml
[pytest]
testpaths = ["tests"]
addopts = [
    "--strict-markers",
    "--strict-config",
    "--cov=src",
    "--cov-branch",
    "--cov-report=term",
    "--cov-report=html",
    "--cov-report=json",
    "--junitxml=junit-report.xml",
]
forgepy_pass_with_no_tests = true
```

`forgepy_pass_with_no_tests` comes from Forge.py's pytest plugin and treats "no tests collected" as success, so a brand-new project's CI passes before it has real tests.

### pre-commit — Git Hooks

`.pre-commit-config.yaml` runs everything through `uv run`, so the hooks use the same tool versions as CI:

| Hook | Stage |
| :--- | :--- |
| `ruff check --fix` | pre-commit |
| `ruff format` | pre-commit |
| `forgepy sync --check` | pre-commit |
| `basedpyright` | pre-push |
| `cz check` (commitizen) | commit-msg — only with versioning on |

Install them with `uv run poe hooks`.

### commitizen — Commit Messages

With versioning on, `[tool.commitizen]` is added to `pyproject.toml`:

```toml
[tool.commitizen]
name = "cz_conventional_commits"
tag_format = "v$version"
```

## Build & Release

### uv_build — Packaging

Backends and libraries use the `uv_build` backend. Backends and websites are marked `Private :: Do Not Upload` so they can never be published to PyPI by accident; websites also set `tool.uv.package = false` because a docs site has no importable module.

### release-please — Versioning

`.github/release.json` configures release-please for a Python project and keeps the version in `uv.lock` in step with `pyproject.toml`:

```json
{
  "packages": {
    ".": {
      "release-type": "python",
      "extra-files": [
        { "type": "toml", "path": "uv.lock", "jsonpath": "$.package[?(@.name.value=='my-project')].version" }
      ]
    }
  }
}
```

`.github/.release.json` is the release-please manifest, starting at `0.1.0`.

### Docker

`--docker` adds a multi-stage `Dockerfile`:

- **Backend:** builds the virtual environment with uv on `python:<version>-slim-bookworm` and runs `python -m <package>` as a non-root `app` user. uv is installed with pip, whose wheels cover every platform `python:slim` does; pass `--build-arg UV_VERSION=<version>` to change it.
- **Website:** builds the static site with Zensical once on the build host and serves it with `nginx:stable-alpine` on port 80.

CI builds the image for every configured platform — see [Job Reference](workflows/reference.md#dockeryml).

### nfpm — Debian Packaging

`--debian` adds `nfpm.yaml`, a systemd unit (`packaging/<name>.service`), a `postinstall.sh`, and `packaging/build_deb.py`. `uv run poe build-deb` builds a relocatable virtual environment against the system Python and packages it as a `.deb`.
