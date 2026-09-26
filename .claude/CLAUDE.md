# Claude Code Instructions

## Subagent Model Routing

The main conversation (Sonnet) is the **orchestrator only** — it delegates work, synthesises results, and makes edits. It does not do bulk reading or deep planning itself.

### When to spawn and which model to use

| Task type | Model | Subagent type |
| --- | --- | --- |
| File reads, searches, grep/glob, log analysis, summarisation | `haiku` | `Explore` |
| Multi-file codebase exploration | `haiku` | `Explore` |
| General coding, edits, refactoring, moderate reasoning | `sonnet` (default, no spawn) | — |
| Architecture decisions, complex multi-file planning | `opus` | `Plan` or `claude` |
| Security review, deep debugging requiring judgment | `opus` | `claude` |
| Code review of a PR or branch | `opus` | `claude` |

### Rules

- **Never read more than ~2 files directly** in the main context. If a task requires reading more, spawn a Haiku `Explore` agent. Direct `Read`/`Grep` results land in the main Sonnet context and inflate cache costs on every subsequent turn. This is backed by a `PreToolUse` hook (`.claude/hooks/read_counter.py`) that counts `Read`/`Grep` calls per session and warns past the threshold — don't rely on memory alone.
- **Always spawn Opus for planning** before implementing anything non-trivial. Let Opus produce the plan, then execute it.
- **Subagent overhead** (~500 tokens cold context) is worth it whenever the agent would read more than a few hundred lines or produce reasoning that would otherwise fill the main context.
- Specify `model:` explicitly on every `Agent` call — never rely on the default for research or planning tasks. `Explore` and `Plan` are pinned to `haiku`/`opus` via `.claude/agents/Explore.md` and `.claude/agents/Plan.md`, so this is now a backstop, not the only enforcement — but `claude` (used for opus-tier review/security work) has no such override and still needs `model: "opus"` passed explicitly every time.

### Example routing

```text
# Exploration / research → Haiku
Agent(subagent_type: "Explore", model: "haiku", prompt: "Find all callers of X and what triggers each call")

# Planning → Opus
Agent(subagent_type: "Plan", model: "opus", prompt: "Design the fix for <problem>")

# Code review → Opus
Agent(subagent_type: "claude", model: "opus", prompt: "Review the changes on this branch for correctness")

# Implementation → Sonnet (main context, no spawn needed)
Edit(...)
```

## Tool Use

- Prefer dedicated tools (Read, Grep, Glob, Edit) over Bash for file operations.
- Use Grep/Glob directly for **single targeted lookups** where the result is small (one file, a few lines).
- For anything broader, spawn a Haiku `Explore` agent — don't dump large files into the main context.
- Never re-read a file you just edited; trust the edit succeeded.
- Run independent tool calls in parallel in a single response rather than sequentially.

## Responses

- Keep responses short and direct. No trailing summaries of what was just done.
- No comments explaining what code does — only add a comment when the *why* is non-obvious.
- No multi-paragraph docstrings or block comment headers.
- Do not add error handling, fallbacks, or abstractions beyond what the task requires.
- Do not suggest follow-up tasks or refactors unless asked.

## Quality Control

- A `PostToolUse` hook (`.claude/hooks/lint_on_edit.py`) runs `ruff check --fix` and `ruff format` on every file touched by `Edit`/`Write` under `src/**` — instant feedback, not a substitute for the checks below.
- Before reporting a non-trivial change complete, run `uv run poe lint && uv run poe type && uv run poe test`.
- Run `/code-review` (medium+) on non-trivial diffs before considering them done; use `/simplify` as a cleanup pass afterward.

## Architecture

forgepy is a Python port of forgejs — a project-scaffolding CLI. `src/forgepy/cli.py` parses argv (`argparse`, strict mode, `BooleanOptionalAction` for `--no-<x>` negation), builds an `InitConfig` (`config.py`), and calls `init()` in `core.py`. `cli.py` also dispatches the separate `forgepy sync` subcommand (`sync.py`) — unrelated to the init pipeline.

`core.py` loads/creates the target project's `pyproject.toml` via `tomlkit` (`pyproject.py` — also where tomlkit's weak type stubs are contained behind typed helpers like `project_name()`/`set_task()`/`ensure_dev_dependency()`, so no other module touches raw tomlkit internals), then runs an ordered **Feature pipeline** (`features/__init__.py` exports `PIPELINE`): `BaseFeature → LintingFeature → BuildFeature → TestingFeature → VersioningFeature → DockerFeature → DebianFeature → WorkflowFeature`. Each feature (`features/*.py`) implements the `Feature` ABC (`features/feature.py`: `should_run`, `apply`, `cleanup`) and is mode-aware (`cfg.mode.is_backend`/`is_library`/`is_website`). Shared helpers in `feature.py`: `create_file`/`create_if_missing` (config vs. source-code write semantics — the latter never overwrites, even with `--force`, since it's the user's own application code), `write_managed` (always refreshes, ignores `--force` — for `.forgepy/`-vendored snapshots), `remove_file`.

Generated file *content* lives in `templates/*.py` as plain (non f-string) string/function exports — GitHub Actions' `${{ }}` syntax collides with both f-string and `string.Template` placeholder syntax, so substitution uses explicit `.replace()` on `__FORGEPY_*__` tokens instead. Unlike forgejs (which points every generated config at `node_modules/@apollogeddon/forgejs/configs/...`), forgepy can't rely on a stable venv path across platforms/Python versions, so only `ruff.toml`/`pyrightconfig.json` use the layered-extends pattern, via a **vendored snapshot**: `configs/{ruff.toml,pyrightconfig.json}` ship as package data, `write_managed()` copies them into the generated project's `.forgepy/` directory, and the project's own `ruff.toml`/`pyrightconfig.json` `extend`/`extends` that local copy. `forgepy sync [--check]` (`sync.py`) is what refreshes that snapshot later — wired into a poe task, a pre-commit hook, and a CI step in generated projects.

`utils/filesystem.py`'s `FileSystem` protocol (`LocalFileSystem` in production, `MemoryFileSystem` for fast unit tests) is what makes `--dry-run` a single code path rather than a parallel one. `tests/test_integration.py` is different: it does a *real* `uv sync` (pointing the `forgepy` dependency at this repo via a `tool.uv.sources` path override, since forgepy isn't published) and runs the real generated poe tasks — this is the only place that catches wiring bugs like a missing dependency (`watchdog`/`validate-pyproject` were both found this way) or a starter file `uv_build`/`tsc`-equivalent checks need but nothing creates.

## Context Management

- Use `/compact` when a session grows long to compress history before continuing.
- Use `/clear` when switching to an unrelated task rather than carrying stale context forward.
