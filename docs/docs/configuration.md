---
title: Configuration
description: What forgepy init generates, and how to override the Forge.py base configs in your project.
---

# Configuration

This page describes each file `forgepy init` generates and how to override it. Forge.py uses a layered model: a project's Ruff and basedpyright configs extend base configs that Forge.py manages, so your project's files hold only what differs.

## Managed configs

The Ruff and basedpyright base configs live in `.forgepy/` inside your project. They are a copy of the configs bundled with the installed version of Forge.py. Extending a local copy, rather than a path inside the virtual environment, keeps the `extend` paths the same on every platform and Python version.

| File | Purpose |
| :--- | :--- |
| `.forgepy/ruff.toml` | Base Ruff rules. Don't edit it: `forgepy sync` overwrites it. |
| `.forgepy/pyrightconfig.json` | Base basedpyright settings. Don't edit it either. |
| `.forgepy/ruff-jython.toml` | Base Ruff rules for [Jython projects](#jython-projects), only in projects that have it. |

`init` always rewrites these files, with or without `--force`.

## Dependencies

`init` adds `forgepy[toolchain]` to the `dev` dependency group in `pyproject.toml`. The `toolchain` extra brings in Ruff, basedpyright, pytest, pytest-cov, Poe the Poet, pre-commit, Commitizen, watchdog and validate-pyproject, with minimum versions only; your `uv.lock` pins the exact versions. Websites also get Zensical, and `--jython` projects get vermin.

As Forge.py isn't on PyPI, `init` also adds a `[tool.uv.sources]` entry that installs it from Git:

```toml
[tool.uv.sources]
forgepy = { git = "https://github.com/apollogeddon/forgepy" }
```

An existing `forgepy` source, such as a local path, is never replaced, even with `--force`.

## Upgrading

To move a project to the latest Forge.py and refresh its managed configs:

```bash
uv lock --upgrade-package forgepy
uv sync
uv run forgepy sync
```

`forgepy sync --check` reports drift without writing anything and exits with status `1` if the snapshot is out of date. The generated pre-commit hook, the `sync-check` task and the CI quality job all run it, so a stale snapshot fails the checks.

## Quality and testing

### Ruff: linting and formatting

The generated `ruff.toml` extends the managed base:

```toml
extend = ".forgepy/ruff.toml"
target-version = "py313"

[lint.per-file-ignores]
"tests/**" = ["S101", "S603", "S607"]
```

The base enables a broad rule set (`E`, `F`, `W`, `I`, `UP`, `B`, `SIM`, `RUF`, `PL`, `N`, `A`, `C4`, `PTH`, `PERF`, `RET`, `ARG` and `S` for Bandit security checks), with a 120-character line length and double quotes. Add project-specific settings below the `extend` line; they take precedence over the base.

### basedpyright: type checking

The generated `pyrightconfig.json` extends the managed base, which runs in strict mode and treats unused imports and variables as errors:

```json
{
  "extends": ".forgepy/pyrightconfig.json",
  "include": ["src", "tests"],
  "venvPath": ".",
  "venv": ".venv"
}
```

`include` lists only the directories that exist for your mode: websites have no `src`, and `--no-testing` drops `tests`.

### pytest: testing

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

`forgepy_pass_with_no_tests` comes from the pytest plugin that Forge.py installs. It treats "no tests collected" as success, so a new project's CI passes before it has real tests. Add `--cov-fail-under` to `addopts` to enforce a coverage threshold; see [Examples](examples.md#enforcing-coverage-thresholds).

### pre-commit: Git hooks

`.pre-commit-config.yaml` runs everything through `uv run`, so the hooks use the same tool versions as CI:

| Hook | Stage |
| :--- | :--- |
| `ruff check --fix` | pre-commit |
| `ruff format` | pre-commit |
| `forgepy sync --check` | pre-commit |
| `basedpyright` | pre-push |
| `poe compat` (vermin and `forgepy check-jython`) | pre-commit, when a file under `src/` changes; only with `--jython` |
| `cz check` (Commitizen) | commit-msg; only with versioning on |

Install them with `uv run poe hooks`.

### Commitizen: commit messages

With versioning on, `[tool.commitizen]` is added to `pyproject.toml`:

```toml
[tool.commitizen]
name = "cz_conventional_commits"
tag_format = "v$version"
```

## Build and release

### uv_build: packaging

Backends and libraries use the `uv_build` build backend. Every mode except `--library` gets the `Private :: Do Not Upload` classifier, so PyPI rejects an accidental upload. Websites and `--jython` projects have no build system and set `[tool.uv] package = false`, as neither has a Python 3 package to install.

### release-please: versioning

With versioning on, `.github/release.json` configures release-please for a Python project and keeps the version in `uv.lock` in step with `pyproject.toml`:

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

- **Backend:** builds the virtual environment with uv on `python:<version>-slim-bookworm` and runs `python -m <package>` as a non-root `app` user. uv is installed with pip, whose wheels cover every platform `python:slim` does. Pass `--build-arg UV_VERSION=<version>` to change its version.
- **Website:** builds the static site with Zensical once on the build host and serves it with `nginx:stable-alpine` on port 80.

CI builds the image for every configured platform. See [docker.yml](workflows/reference.md#dockeryml) in the job reference.

### nFPM: Debian packaging

`--debian` adds `nfpm.yaml`, a systemd unit (`packaging/<name>.service`), `packaging/postinstall.sh` and `packaging/build_deb.py`. `uv run poe build-deb` builds a relocatable virtual environment against the system Python and packages it as a `.deb` that installs to `/opt/<name>` and depends on `python3`. It needs the `nfpm` CLI on your `PATH`.

## Jython projects

`forgepy init --jython` is for scripts that run on Jython 2.7, such as an application platform's scripting layer. The tools still run on CPython 3: uv installs them and the test suite, but doesn't build or install the project itself (`[tool.uv] package = false`, no build system and no `build` task). Scripts go under `src/`, and `pytest.toml` puts `src` on the import path.

Ruff can't target Python 2, so the checks keep the code within the subset both versions share:

- `ruff.toml` extends `.forgepy/ruff-jython.toml`, a managed base that extends forgepy's usual one and turns off the rules whose fixes need Python 3: `UP` (f-strings, `super()` without arguments and other upgrades), `PTH` (pathlib), `B904` (`raise ... from`), `SIM105` (`contextlib.suppress`), `RUF005`, `RUF012` and `F401`. It targets `py37`, the oldest version Ruff supports, and `ruff.toml` targets the tests at your Python version instead, as they run on CPython. `forgepy sync` refreshes the base in projects that have it. A `select` or `extend-select` in your own `ruff.toml` turns those rules back on, as it comes after the base's `ignore`, so list them in your `ignore` or `per-file-ignores` again if you select more rules.
- Python 2 code annotates with type comments and imports their names under `if MYPY:`, which Jython never runs. `pyrightconfig.json` defines `MYPY` as true so basedpyright follows those imports, and turns off `reportTypeCommentUsage`. basedpyright stays in strict mode; relax `typeCheckingMode` in your own `pyrightconfig.json` if a platform's stubs need it. It also reports the unused imports that Ruff's `F401` would, since it reads the type comments.
- The `compat` task runs [vermin](https://github.com/netromdk/vermin) over `src/` and fails on any syntax, module or function Jython 2.7 doesn't have. vermin reads no `pyproject.toml` settings, so its options are in the task; it ignores the `typing` module, as the scripts import it only for type comments. The task then runs `forgepy check-jython src`, which finds a comma after `*args` or `**kwargs`: `ruff format` adds one when it puts each argument on its own line, Python 2 rejects it, and vermin can't see it. Shorten the call or definition so it fits on fewer lines, or keep the formatter off it with `# fmt: off` and `# fmt: on`. The pre-commit hook runs the task when a file under `src/` changes, and CI runs it in the quality job.
- basedpyright checks the scripts as Python 3, so it doesn't know Python 2's builtins. A script that uses `unicode`, `basestring`, `long` or `xrange` needs them declared in a `__builtins__.pyi` at the project root, for example `unicode = str`.

The tests run on CPython 3, so vermin doesn't check them, but Ruff applies the same rules to them as to the scripts.

If the scripts are type-checked against several versions of a platform's stubs, put each version in its own dependency group and pass `sync_args` (for example `--no-default-groups --group dev --group stubs-v2`) to `testing.yml` from a matrix job.

## Python version

A project's Python version lives in `.python-version`, which `init` writes with `3.13`, or the version passed to `--python`, and which uv and `actions/setup-python` both read. `requires-python` in `pyproject.toml` starts from the same version.

Every workflow job that sets up Python picks the version in this order:

1. The `python_version` input, when the caller sets one.
2. The project's `.python-version`.
3. Python 3.13, forgepy's default, when the project has neither.

So moving a project to another version is one edit to `.python-version`, with `requires-python` and Ruff's target version to match.

## Repository files

`init` also writes three files for the repository itself. Like the other configs, an existing one is kept unless you pass `--force`.

| File | What it does |
| :--- | :--- |
| `.editorconfig` | LF line endings, UTF-8 and 120 columns, with 4-space Python and 2-space everything else, matching the Ruff config |
| `.github/dependabot.yml` | Weekly uv and GitHub Actions updates, plus Docker with `--docker`. Minor and patch updates are grouped into one pull request, and each update waits 3 days after it's published before it's proposed, so a compromised release has time to be caught upstream. The workflow's auto-merge job merges them once CI passes. |
| `.github/CODEOWNERS` | `* @owner`, so every pull request someone else opens, Dependabot's and release-please's included, requests your review and shows in your review requests. It doesn't block merging. |

The `CODEOWNERS` owner is the GitHub account in a `[project.urls]` entry of `pyproject.toml` or, failing that, the `origin` remote. A project with neither gets no `CODEOWNERS`; run `init` again once it has a GitHub remote.
