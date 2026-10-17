<br />
<div align="center">
  <a href="https://apollogeddon.github.io/forgepy/">
    <img src="docs/docs/assets/forgepy.svg" alt="Forge.py logo" width="100" height="100">
  </a>

  <h3 align="center">Forge.py</h3>

  <p align="center">
    Reusable GitHub Actions workflows and tooling configurations for Python projects
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

Forge.py (`forgepy`) is a project-scaffolding CLI for Python. Its `init` command sets up a uv-managed backend, library or website with a standard toolchain and a GitHub Actions pipeline built from reusable workflows. It keeps your lint, type-check and test setup in one place: the generated configs extend a shared base that `forgepy sync` keeps current, so every project stays on the same rules.

## Requirements

- [uv](https://docs.astral.sh/uv/): Forge.py generates uv-managed projects, and every task runs through `uv run`
- Python: the version you pass to `--python`, the one your project already pins, or Forge.py's default; uv can install it for you
- Git, for the generated pre-commit hooks

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

- Writes tool configs: `ruff.toml`, `pyrightconfig.json`, `pytest.toml`, `.pre-commit-config.yaml`, the release-please config and `.github/workflows/.index.yml`, plus a `Dockerfile`, `nfpm.yaml` or `mkdocs.yml` depending on the mode.
- Writes the repository files `.editorconfig`, `.gitignore`, `.github/dependabot.yml` and `.github/CODEOWNERS`.
- Adds tasks such as `lint`, `type`, `test` and `build` to `[tool.poe.tasks]` in `pyproject.toml`.
- Creates a starter package so `uv sync` and the generated tasks work straight away.

It is safe to re-run: existing files and tasks are left alone unless you pass `--force`, and your own source code is never overwritten.

## Keeping projects up to date

Forge.py itself is installed from Git, pinned in `[tool.uv.sources]` to the release tag that ran `init`. The Ruff and basedpyright base configs are copied into `.forgepy/`, and the project's `ruff.toml` and `pyrightconfig.json` extend them. To pick up a newer Forge.py and its configs, change the tag (`forgepy = { git = "...", tag = "vX.Y.Z" }`), then:

```bash
uv lock
uv sync
uv run forgepy sync
```

`forgepy sync --check` reports a stale `.forgepy/` without writing anything. The generated pre-commit hook and CI both run it. See [Configuration](https://apollogeddon.github.io/forgepy/configuration/) for details.

## Documentation

The full documentation is at [apollogeddon.github.io/forgepy](https://apollogeddon.github.io/forgepy/):

- [Getting started](https://apollogeddon.github.io/forgepy/getting-started/): requirements, CLI flags and generated tasks.
- [Configuration](https://apollogeddon.github.io/forgepy/configuration/): the files Forge.py writes and how to change them.
- [Examples](https://apollogeddon.github.io/forgepy/examples/): common configuration and workflow recipes.
- [Workflows](https://apollogeddon.github.io/forgepy/workflows/overview/): the reusable GitHub Actions pipelines, the generated `.index.yml` that calls them, and their inputs.
- [Migration](https://apollogeddon.github.io/forgepy/migration/): adopting Forge.py in a project that already has tooling.

## Contributing

Pull requests are welcome. The [contributing guide](https://apollogeddon.github.io/forgepy/contributing/) covers setting up the repository, the checks to run before opening a pull request, and the commit message format releases are generated from.

## License

Forge.py is released under the [MIT License](LICENSE).
