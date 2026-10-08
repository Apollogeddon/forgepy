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

## Jython projects

`forgepy init --jython` is for scripts that run on Jython 2.7, such as an application platform's scripting layer. The tools still run on CPython 3: uv installs them and the test suite, but doesn't build or install the project itself (`[tool.uv] package = false`, no build system and no `build` task). Scripts go under `src/`, and `pytest.toml` puts `src` on the import path.

Ruff can't target Python 2, so the checks keep the code within the subset both versions share:

- `ruff.toml` extends `.forgepy/ruff-jython.toml`, a managed base that extends forgepy's usual one and turns off the rules whose fixes need Python 3: `UP` (f-strings, `super()` without arguments and other upgrades), `PTH` (pathlib), `B904` (`raise ... from`), `SIM105` (`contextlib.suppress`), `RUF005`, `RUF012` and `F401`. It targets `py37`, the oldest version Ruff supports, and `ruff.toml` targets the tests at your Python version instead, as they run on CPython. `forgepy sync` refreshes the base in projects that have it. A `select` or `extend-select` in your own `ruff.toml` turns those rules back on, as it comes after the base's `ignore`, so list them in your `ignore` or `per-file-ignores` again if you select more rules.
- Python 2 code annotates with type comments and imports their names under `if MYPY:`, which Jython never runs. `pyrightconfig.json` defines `MYPY` as true so basedpyright follows those imports, and turns off `reportTypeCommentUsage`. basedpyright stays in strict mode; relax `typeCheckingMode` in your own `pyrightconfig.json` if a platform's stubs need it. It also reports the unused imports that Ruff's `F401` would, since it reads the type comments.
- The `compat` task runs [vermin](https://github.com/netromdk/vermin) over `src/` and fails on any syntax, module or function Jython 2.7 doesn't have. vermin reads no `pyproject.toml` settings, so its options are in the task; it ignores the `typing` module, as the scripts import it only for type comments. The task then runs `forgepy check-jython src`, which finds a comma after `*args` or `**kwargs`: `ruff format` adds one when it puts each argument on its own line, Python 2 rejects it, and vermin can't see it. Shorten the call or definition so it fits on fewer lines, or keep the formatter off it with `# fmt: off` and `# fmt: on`. The pre-commit hook runs the task when a file under `src/` changes, and CI runs it in the quality job.
- basedpyright checks the scripts as Python 3, so it doesn't know Python 2's builtins. A script that uses `unicode`, `basestring`, `long` or `xrange` needs them declared in a `__builtins__.pyi` at the project root, for example `unicode = str`.

The tests run on CPython 3, so vermin doesn't check them, but Ruff applies the same rules to them as to the scripts.

If the scripts are type-checked against several versions of a platform's stubs, put each version in its own dependency group and pass `sync_args` (for example `--no-default-groups --group dev --group stubs-v2`) to `testing.yml` from a matrix job.

