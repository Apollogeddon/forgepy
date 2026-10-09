---
title: Quality tooling, zero configuration drift
home: true
hide:
  - navigation
  - toc
---

<div class="fp-hero" markdown>

<span class="fp-badge">Python 3.13 · uv · forgepy</span>

# Quality tooling,<br>zero configuration drift.

<p class="fp-lead">Reusable GitHub Actions workflows and tooling configurations for Python projects. Keep your Ruff, basedpyright and pytest setup in one place, and scaffold projects with one command.</p>

<div class="fp-buttons" markdown>

[Get started :material-arrow-right:](getting-started.md){ .md-button .md-button--primary }
[:fontawesome-brands-github: GitHub](https://github.com/Apollogeddon/forgepy){ .md-button }

</div>

<div class="fp-terminal">
<div class="fp-terminal-bar"><span></span><span></span><span></span>bash</div>
<pre><code><span class="fp-prompt">$ </span>uv tool install git+https://github.com/apollogeddon/forgepy
<span class="fp-prompt">$ </span>forgepy init
<span class="fp-ok">✓ Configuration files created</span>
<span class="fp-ok">✓ Poe tasks added</span>
<span class="fp-next">  Forge.py ready.</span></code></pre>
</div>

</div>

## Why Forge.py { .fp-section-title }

<p class="fp-section-lead">The tooling and CI/CD a Python project needs, in one tool.</p>

<div class="grid cards fp-cols-2" markdown>

-   :lucide-settings:{ .fp-icon } __Standardised tooling__

    Shared Ruff and basedpyright configs give every project the same checks from day one, and `forgepy sync` keeps them current.

-   :lucide-workflow:{ .fp-icon } __Reusable workflows__

    GitHub Actions workflows for testing, building, releasing and deploying. `init` writes the workflow that calls them.

-   :lucide-rocket:{ .fp-icon } __Project scaffolding__

    `init` sets up a backend, library or website, with optional Docker and Debian packaging and no boilerplate to copy.

-   :lucide-tag:{ .fp-icon } __Automated releases__

    release-please derives versions and changelogs from Conventional Commits, and the pipeline publishes each release.

</div>

## Quick start { .fp-section-title }

<p class="fp-section-lead">From empty repo to a standardised toolchain in three steps.</p>

<div class="fp-steps" markdown>

<div class="fp-step" markdown>
<div class="fp-step-n">01</div>
<div markdown>

__Install__

Install Forge.py from GitHub as a uv tool.

```bash
uv tool install git+https://github.com/apollogeddon/forgepy
```

</div>
</div>

<div class="fp-step" markdown>
<div class="fp-step-n">02</div>
<div markdown>

__Initialise__

Run the CLI to scaffold configs, tasks and the CI workflow.

```bash
forgepy init
```

</div>
</div>

<div class="fp-step" markdown>
<div class="fp-step-n">03</div>
<div markdown>

__Extend__

The generated configs extend the shared ones. Add project-specific settings alongside.

```toml
# ruff.toml
extend = ".forgepy/ruff.toml"
target-version = "py313"
```

</div>
</div>

</div>

<p class="fp-more"><a href="getting-started/">Full documentation →</a></p>

## The toolchain { .fp-section-title }

<p class="fp-section-lead">Fast tools, pinned by Forge.py and run through poe tasks.</p>

<div class="grid cards fp-cols-4 fp-tools" markdown>

-   __Ruff__ <span class="fp-chip fp-chip--rust">Rust</span>

    Replaces Flake8, isort, Black

-   __pytest__ <span class="fp-chip fp-chip--python">Python</span>

    Replaces unittest, nose

-   __basedpyright__ <span class="fp-chip fp-chip--js">Node</span>

    Replaces mypy, Pyright

-   __pre-commit__ <span class="fp-chip fp-chip--python">Python</span>

    Replaces hand-written Git hooks

-   __release-please__ <span class="fp-chip fp-chip--js">JS</span>

    Replaces manual tagging

-   __Commitizen__ <span class="fp-chip fp-chip--python">Python</span>

    Replaces manual commit review

-   __uv__ <span class="fp-chip fp-chip--rust">Rust</span>

    Replaces pip, venv, Poetry

-   __Poe the Poet__ <span class="fp-chip fp-chip--python">Python</span>

    Replaces Makefiles

</div>
