# Claude Code Instructions

General working rules (subagent routing, tool use, response style) live in the user-level `~/.claude/CLAUDE.md`. This file is project-specific.

## Reading the codebase

`src/` is ~1.5k lines and `tests/` ~800: read what you need directly rather than delegating. Use an `Explore` agent only for `.venv`. `uv.lock`, `htmlcov/`, `coverage.json`, `.coverage` and `junit-report.xml` are denied to `Read` in `settings.json` — use `uv tree` to check a resolved version.

A `PostToolUse` hook (`.claude/hooks/read_counter.py`) reminds you past 10 Read/Grep/Glob calls in a session.

## Quality Control

- A `PostToolUse` hook (`.claude/hooks/lint_on_edit.py`) runs `ruff check --fix` and `ruff format` on every `.py` file touched by `Edit`/`Write`. Errors it can't fix are returned to you — fix them before moving on.
- While iterating, run `uv run poe test:unit` (quiet, no coverage table, skips the slow real-`uv sync` integration tests).
- Before reporting a non-trivial change complete, run `uv run poe lint && uv run poe type && uv run poe test`. Always run the full `uv run poe test` when a change touches config wiring, dependencies or the vendored `configs/` snapshot — only the integration tests catch those.
- Run `/code-review` (medium+) on non-trivial diffs before considering them done; use `/simplify` as a cleanup pass afterward.

## Architecture

forgepy is a project-scaffolding CLI. `src/forgepy/cli.py` parses argv (`argparse`, strict mode, `BooleanOptionalAction` for `--no-<x>` negation), builds an `InitConfig` (`config.py`), and calls `init()` in `core.py`. `cli.py` also dispatches the separate `forgepy sync` subcommand (`sync.py`) — unrelated to the init pipeline.

`core.py` loads/creates the target project's `pyproject.toml` via `tomlkit` (`pyproject.py` — also where tomlkit's weak type stubs are contained behind typed helpers like `project_name()`/`set_task()`/`ensure_dev_dependency()`, so no other module touches raw tomlkit internals), then runs an ordered **Feature pipeline** (`features/__init__.py` exports `PIPELINE`): `BaseFeature → LintingFeature → BuildFeature → TestingFeature → VersioningFeature → DockerFeature → DebianFeature → WorkflowFeature`. Each feature (`features/*.py`) implements the `Feature` ABC (`features/feature.py`: `should_run`, `apply`, `cleanup`) and is mode-aware (`cfg.mode.is_backend`/`is_library`/`is_website`). Shared helpers in `feature.py`: `create_file`/`create_if_missing` (config vs. source-code write semantics — the latter never overwrites, even with `--force`, since it's the user's own application code), `write_managed` (always refreshes, ignores `--force` — for `.forgepy/`-vendored snapshots), `remove_file`.

Generated file *content* lives in `templates/*.py` as plain (non f-string) string/function exports — GitHub Actions' `${{ }}` syntax collides with both f-string and `string.Template` placeholder syntax, so substitution uses explicit `.replace()` on `__FORGEPY_*__` tokens instead. forgepy can't point generated configs at an installed package path, since the venv path isn't stable across platforms/Python versions, so only `ruff.toml`/`pyrightconfig.json` use the layered-extends pattern, via a **vendored snapshot**: `configs/{ruff.toml,pyrightconfig.json}` ship as package data, `write_managed()` copies them into the generated project's `.forgepy/` directory, and the project's own `ruff.toml`/`pyrightconfig.json` `extend`/`extends` that local copy. `forgepy sync [--check]` (`sync.py`) is what refreshes that snapshot later — wired into a poe task, a pre-commit hook, and a CI step in generated projects.

`utils/filesystem.py`'s `FileSystem` protocol (`LocalFileSystem` in production, `MemoryFileSystem` for fast unit tests) is what makes `--dry-run` a single code path rather than a parallel one. `tests/test_integration.py` is different: it does a *real* `uv sync` (pointing the `forgepy` dependency at this repo via a `tool.uv.sources` path override, since forgepy isn't published) and runs the real generated poe tasks — this is the only place that catches wiring bugs like a missing dependency (`watchdog`/`validate-pyproject` were both found this way) or a starter file `uv_build`/`tsc`-equivalent checks need but nothing creates.

**CI.** The reusable pipelines in `.github/workflows/` are `workflow_call` only, split by role, and never call each other, so a run page reads `<pipeline> / <stage>`: `library`, `service` and `website` (lint, scan, test, build, and a website's check), `debian`, `docker`, `version`, `publish`, `pages`, `patch` and `merge`. This repository's own CI is the root `.github/workflows/.index.yml`, which calls them locally; its jobs are named after the pipelines. `init` writes a project's `.github/workflows/.index.yml` from `templates/workflows.py` (`index_workflow`), calling them at `@main`. In both, `patch` runs on the schedule, a manual run and the `auto-merged` dispatch `merge` sends after a Dependabot merge, and concurrency cancels only a pull request's older run.

`init` then removes an `index.yml` that calls forgepy's pipelines (`remove_old_workflows` in `features/workflows.py`), only once `.index.yml` was written. One whose normalised hash is in `templates/legacy.py` goes; one that calls forgepy's pipelines but was changed goes only with `--force`; one that calls none is the project's own and stays. The hashes cover every release's output across modes and flags, with samples in `tests/fixtures/legacy/`; `templates/legacy.py` says how they were made. Never change a hash to make a test pass.

## Change checklist

Adding or changing a CLI flag or feature usually touches all of these — check each one before calling it done:

1. `src/forgepy/cli.py` — the `add_argument` call (`BooleanOptionalAction` for standard features) and its help text.
2. `src/forgepy/config.py` — the `InitConfig` field.
3. `src/forgepy/features/<feature>.py` — `should_run`/`apply`/`cleanup`; register new features in `PIPELINE` in `features/__init__.py`, in pipeline order.
4. `src/forgepy/templates/<name>.py` — generated content; `src/forgepy/configs/` + `sync.py` if it changes the vendored snapshot.
5. Tests: `tests/test_cli.py` / `test_core.py` (unit); `test_integration.py` if it changes what gets installed or run; `test_actions.py` for workflow templates and the pipelines (actionlint runs over both when it's installed); `test_sync.py` for snapshot changes.
6. Docs: `docs/docs/getting-started.md` (flag and task reference), `configuration.md`, `workflows/*.md` for workflow changes, and `README.md` for user-facing changes.
