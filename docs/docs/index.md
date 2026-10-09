---
title: Quality tooling, zero configuration drift
hide:
  - navigation
  - toc
---

<div class="fp-hero" markdown>

<span class="fp-badge">Python 3.13 · uv · forgepy</span>

# Quality tooling,<br>zero configuration drift.

<p class="fp-lead">Forge.py is a command-line tool that scaffolds linting, type checking, testing, releases and GitHub Actions CI into uv-managed Python projects, and keeps their Ruff, basedpyright and pytest setup in one place.</p>

<div class="fp-buttons" markdown>

[Get started :material-arrow-right:](getting-started.md){ .md-button .md-button--primary }
[:fontawesome-brands-github: GitHub](https://github.com/Apollogeddon/forgepy){ .md-button }

</div>

<div class="fp-terminal">
<div class="fp-terminal-bar"><span></span><span></span><span></span>bash</div>
<pre><code><span class="fp-prompt">$ </span>uv tool install git+https://github.com/apollogeddon/forgepy
<span class="fp-prompt">$ </span>forgepy init
<span class="fp-ok">✓ Configuration files created</span>
<span class="fp-ok">✓ forgepy init complete</span>
<span class="fp-next">  Next steps: uv sync &amp;&amp; uv run poe hooks</span></code></pre>
</div>

</div>

## Why Forge.py { .fp-section-title }

<p class="fp-section-lead">The tooling and CI/CD a Python project needs, in one command.</p>

<div class="grid cards fp-cols-2" markdown>

-   :material-tune-variant:{ .fp-icon } __Shared tool configs__

    Every project extends the same Ruff and basedpyright base configs, and `forgepy sync` keeps them current.

-   :material-source-branch-sync:{ .fp-icon } __Reusable workflows__

    GitHub Actions workflows for checks, builds, releases and delivery. `forgepy init` generates the caller for your project.

-   :material-folder-plus-outline:{ .fp-icon } __Project scaffolding__

    `forgepy init` sets up a backend, library or documentation site, with optional Docker and Debian packaging.

-   :material-tag-arrow-up-outline:{ .fp-icon } __Automated releases__

    release-please derives versions and changelogs from Conventional Commits, and the pipeline publishes each release.

</div>

## Quick start { .fp-section-title }

<p class="fp-section-lead">From empty repo to a standardised toolchain in three steps.</p>

<div class="fp-steps" markdown>

<div class="fp-step" markdown>
<div class="fp-step-n">01</div>
<div markdown>

__Install__

Forge.py isn't on PyPI. Install it from GitHub as a uv tool.

```bash
uv tool install git+https://github.com/apollogeddon/forgepy
```

</div>
</div>

<div class="fp-step" markdown>
<div class="fp-step-n">02</div>
<div markdown>

__Scaffold__

Run `init` in your project to write the configs, tasks and CI workflow.

```bash
forgepy init
```

</div>
</div>

<div class="fp-step" markdown>
<div class="fp-step-n">03</div>
<div markdown>

__Set up__

Install the toolchain and the Git hooks.

```bash
uv sync
uv run poe hooks
```

</div>
</div>

</div>

<p class="fp-more"><a href="getting-started/">Full documentation →</a></p>

## The toolchain { .fp-section-title }

<p class="fp-section-lead">Fast, modern tools behind one set of poe tasks.</p>

<div class="grid cards fp-cols-4 fp-tools" markdown>

-   __Ruff__ <span class="fp-chip fp-chip--rust">Rust</span>

    Replaces Flake8, isort, Black

-   __basedpyright__ <span class="fp-chip fp-chip--js">Node</span>

    Replaces mypy, Pyright

-   __uv__ <span class="fp-chip fp-chip--rust">Rust</span>

    Replaces pip, venv, Poetry

-   __pytest__ <span class="fp-chip fp-chip--python">Python</span>

    Replaces unittest, nose

-   __Poe the Poet__ <span class="fp-chip fp-chip--python">Python</span>

    Replaces Makefiles, ad-hoc scripts

-   __pre-commit__ <span class="fp-chip fp-chip--python">Python</span>

    Replaces manual pre-commit checks

-   __Commitizen__ <span class="fp-chip fp-chip--python">Python</span>

    Replaces manual commit review

-   __release-please__ <span class="fp-chip fp-chip--js">JS</span>

    Replaces manual tagging and changelogs

</div>
