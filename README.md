<br />
<div align="center">
  <a href="https://apollogeddon.github.io/forgepy/">
    <img src="docs/docs/assets/forgepy.svg" alt="Forge.py logo" width="100" height="100">
  </a>

  <h3 align="center">Forge.py</h3>

  <p align="center">
    Quality tooling and CI/CD for Python projects, scaffolded with one command.
    <br />
    <a href="https://apollogeddon.github.io/forgepy/"><strong>Read the docs</strong></a>
    <br />
    <br />
    <a href="https://apollogeddon.github.io/forgepy/getting-started/">Getting started</a>
    &middot;
    <a href="https://apollogeddon.github.io/forgepy/configuration/">Configuration</a>
    &middot;
    <a href="https://apollogeddon.github.io/forgepy/workflows/overview/">Workflows</a>
  </p>
</div>

<br />

Forge.py (`forgepy`) is a command-line tool that sets up linting, type checking, testing, Git hooks, releases and GitHub Actions CI in a uv-managed Python project. It is for teams that want every repository to use the same toolchain and configuration, and to upgrade it in one place.

## Installation

Forge.py isn't published to PyPI. Install it from GitHub with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install git+https://github.com/apollogeddon/forgepy
```

Or run it once without installing:

```bash
uvx --from git+https://github.com/apollogeddon/forgepy forgepy init
```

## Quick start

Run `init` in an existing project, or in an empty directory to start a new one, then install the toolchain and Git hooks:

```bash
forgepy init
uv sync
uv run poe hooks
```

`init` scaffolds a backend service by default. Pick another mode with a flag:

| Flag | Project type |
| :--- | :--- |
| `--backend` | Python service or application (default) |
| `--library` | Package published to PyPI |
| `--website` | Static documentation site built with [Zensical](https://zensical.org/) |

Add `--jython` to a backend for scripts that run on Jython 2.7, or `--docker` and `--debian` for container and `.deb` packaging. Run `forgepy init --help` for every flag, or see the [flag reference](https://apollogeddon.github.io/forgepy/getting-started/#cli-options).

`init` does the following:

- Writes tool configs: `ruff.toml`, `pyrightconfig.json`, `pytest.toml`, `.pre-commit-config.yaml`, the release-please config and `.github/workflows/index.yml`, plus a `Dockerfile`, `nfpm.yaml` or `mkdocs.yml` depending on the mode.
- Adds tasks such as `lint`, `type`, `test` and `build` to `[tool.poe.tasks]` in `pyproject.toml`.
- Creates a starter package so `uv sync` and the generated tasks work straight away.

It is safe to re-run: existing files and tasks are left alone unless you pass `--force`, and your own source code is never overwritten.

## Toolchain

| Category | Tool |
| :--- | :--- |
| Linting and formatting | [Ruff](https://docs.astral.sh/ruff/) |
| Type checking | [basedpyright](https://docs.basedpyright.com/) |
| Testing | [pytest](https://docs.pytest.org/) with pytest-cov |
| Tasks | [Poe the Poet](https://poethepoet.natn.io/) |
| Git hooks | [pre-commit](https://pre-commit.com/) |
| Commit messages | [Commitizen](https://commitizen-tools.github.io/commitizen/) |
| Releases | [release-please](https://github.com/googleapis/release-please) |
| Security scanning (CI) | [Gitleaks](https://github.com/gitleaks/gitleaks) and [OSV-Scanner](https://google.github.io/osv-scanner/) |
| CI/CD | Reusable [GitHub Actions](https://docs.github.com/actions) workflows |
| Containers (`--docker`) | Multi-platform images built with Docker Buildx and pushed to GHCR on release |
| Debian packages (`--debian`) | [nFPM](https://nfpm.goreleaser.com/) |

## Keeping projects up to date

A generated project depends on `forgepy[toolchain]` as a dev dependency, which sets minimum versions for the tools. The project's own `uv.lock` pins the exact versions.

The Ruff and basedpyright base configs are copied into `.forgepy/`, and the project's `ruff.toml` and `pyrightconfig.json` extend them. To pick up a newer Forge.py and its configs:

```bash
uv lock --upgrade-package forgepy
uv sync
uv run forgepy sync
```

`forgepy sync --check` reports a stale `.forgepy/` without writing anything. The generated pre-commit hook and CI both run it. See [Configuration](https://apollogeddon.github.io/forgepy/configuration/) for details.

## Documentation

The full documentation is at [apollogeddon.github.io/forgepy](https://apollogeddon.github.io/forgepy/).

## License

Forge.py is released under the [MIT License](LICENSE).
