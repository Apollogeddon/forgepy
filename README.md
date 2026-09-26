# forgepy

Quality control and DevOps scaffolding for modern Python projects.

`forgepy init` sets up linting, type-checking, testing, CI/CD, and packaging in one pass — so every project you start (or already have) ends up with the same solid baseline instead of hand-rolling it each time.

## Installation

```bash
uv tool install forgepy
```

Or run it once without installing:

```bash
uvx forgepy init
```

## Getting started

```bash
forgepy init [options]
```

By default this sets up a **backend/service** project. Other modes:

* `--backend` (default) — services and applications
* `--library` — publishable PyPI packages
* `--website` — static documentation sites (mkdocs)

Running `init`:

* **Scaffolds config** — `ruff.toml`, `pyrightconfig.json`, `pytest.toml`, `.pre-commit-config.yaml`, and mode-specific files (`Dockerfile`, `nfpm.yaml`, `mkdocs.yml`, ...)
* **Wires up tasks** — adds `lint`, `type`, `test`, `build`, and more to `[tool.poe.tasks]` in `pyproject.toml`
* **Creates a starter package** — `src/<name>/__init__.py` (and `__main__.py` for backends), so `uv sync` and the generated tooling work immediately on a brand-new project
* **Is safe to re-run** — existing files are left alone unless you pass `--force`

Run `forgepy init --help` for the full flag reference (each one is self-documenting), or `forgepy --help` for all commands.

## Standardized stack

| Category | Tool |
| :--- | :--- |
| **Linting & formatting** | [Ruff](https://docs.astral.sh/ruff/) |
| **Type checking** | [basedpyright](https://docs.basedpyright.com/) (strict mode) |
| **Testing** | [pytest](https://docs.pytest.org/) + coverage |
| **Task running** | [poethepoet](https://poethepoet.natn.io/) |
| **Git hooks** | [pre-commit](https://pre-commit.com/) |
| **Commit linting** | [commitizen](https://commitizen-tools.github.io/commitizen/) |
| **Releases** | [release-please](https://github.com/googleapis/release-please) |
| **Security scanning** | [Gitleaks](https://github.com/gitleaks/gitleaks) + [OSV-Scanner](https://osv.dev/) |
| **CI/CD** | Reusable GitHub Actions workflows (quality, testing, versioning, publish) |
| **Docs sites** | [MkDocs Material](https://squidfunk.github.io/mkdocs-material/) (`--website`) |
| **Debian packages** | [nfpm](https://nfpm.goreleaser.com/) (`--backend --debian`) |

## Keeping configs current: `forgepy sync`

forgepy ships its own `ruff.toml`/`pyrightconfig.json` as the base every generated project extends, vendored into a project's `.forgepy/` directory at init time. When forgepy itself updates those defaults, run:

```bash
forgepy sync          # refresh the vendored configs
forgepy sync --check  # report drift without writing (exit 1 if out of date)
```

`sync --check` is already wired into the generated pre-commit hook and CI, so drift gets caught automatically.

## Philosophy

* **One place to upgrade.** forgepy bundles its own toolchain versions (ruff, basedpyright, pytest, ...) as dependencies — bump `forgepy` and every tool it configured moves with it.
* **Real tests, not just file checks.** Every mode is exercised end-to-end (`uv sync` + the full generated task list) before a change ships, not just checked for the right files existing.
* **Security by default.** Gitleaks and OSV-Scanner run in every generated CI pipeline, with a cooldown period on dependency updates.
