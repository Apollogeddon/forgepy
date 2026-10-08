---
title: Job Reference
description: Job-by-job breakdown of each reusable workflow.
---

# Job Reference

## Pipeline Overview

Every pipeline follows the same three stages:

1. **Quality & testing** — `testing.yml` runs `quality.yml`, the test suite and the build.
2. **Versioning** — `version.yml` runs release-please on the main branch.
3. **Delivery** — `library.yml` (PyPI), `debian.yml` (Linux), `website.yml` (GitHub Pages) or `docker.yml` (GHCR) publishes the result.

Dependabot pull requests are auto-merged by `merge.yml` once testing passes.

`service.yml`, `website.yml` and `debian.yml` expose `version.yml`'s `new_release_published`, `version` and `tag_name` as outputs, which the generated `docker` job uses to decide when to push.

## Choosing runners

Every workflow takes a `runs_on` input, default `ubuntu-latest`, and passes it down to each workflow it calls, so every job runs on that runner label. Set it per repository to use self-hosted runners, e.g. from a repository variable: `runs_on: ${{ vars.RUNS_ON || 'ubuntu-latest' }}`.

`docker.yml`'s per-platform builds and its manifest merge use GitHub-hosted runners: the builds because they need native Arm machines, the merge because it needs a Docker daemon. With `buildkit_endpoint` set, it builds every platform in one job on `runs_on` instead, against a remote BuildKit, so self-hosted runners without a Docker daemon can build and push multi-platform images. `debian.yml`'s `build-deb` stays on `ubuntu-latest` too, as it builds inside a Debian container.

## Checking once per change

By default the checks run on every push and pull request, so a change is checked on its PR, again on `main`, and again around its release. To check each change only on its pull request:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  schedule:
    - cron: '17 3 * * 1'   # weekly: a full check of main

concurrency:
  group: ${{ github.workflow }}-${{ github.head_ref || github.run_id }}
  cancel-in-progress: true

jobs:
  service:
    uses: apollogeddon/forgepy/.github/workflows/service.yml@main
    with:
      test_on_push: false        # pushes to main only run release-please
      # test_release_prs: false  # also skip release-please's release PRs
```

- Pull requests run the full checks. A newer push cancels the run it replaces, and `main`'s own runs are never cancelled.
- Pushes to `main` run only release-please and anything after it.
- Release PRs run the checks unless `test_release_prs` is `false`. When they do run, they're the one place every change since the last release is checked together.
- Skipped jobs count as passed for required status checks.
- With `test_on_push: false`, turn off **Require branches to be up to date before merging**. Otherwise every PR is checked again before merge.

`library.yml`, `debian.yml` and `website.yml` take `test_on_push` too. There, a push to `main` runs release-please first, and only when it makes a release does it run the checks, the build, and the publish, package or deploy that ships what they built. A `website.yml` caller with `enable_versioning: false` deploys every push, so its pushes are always checked.

In that mode release-please tags the release before the push's checks run. If they fail, the tag and the GitHub release exist with nothing published, and need putting right by hand. So with these three, keep `test_release_prs: true`: the release PR is then checked with exactly what its merge ships.

## quality.yml

*Security and static analysis.*

1. **`secure`** — Gitleaks secret scan (skip with `enable_secrets: false`) and an OSV-Scanner dependency scan.
2. **`linting`** — `uv sync --locked` (plus `sync_args`), then `ruff check`, `ruff format --check`, `basedpyright` and `forgepy sync --check`. In a `--jython` project (one with `.forgepy/ruff-jython.toml`) it also runs `poe compat`, the vermin Jython 2.7 check.

## testing.yml

*The full QA suite.*

1. Calls → `quality.yml`.
2. **`testing`** — `uv sync --locked` and `pytest` (skip with `run_tests: false`); uploads the coverage report.
3. **`build`** — Runs `build_command` (default `uv build`) and uploads the result as the `artifact_name` artifact. It runs alongside `testing`, once `quality` passes. Skip it with `run_build: false`, for a project with nothing to build.
4. **`patch`** — On `main` with `auto_patch` enabled, scans `uv.lock` with OSV-Scanner, upgrades just the vulnerable packages with `uv lock --upgrade-package` (transitive ones included, within the ranges `pyproject.toml` allows, without building any package), and commits the new `uv.lock`. OSV-Scanner can't fix a `uv.lock` in place, so uv does the upgrade. *(Needs: quality, testing, build)*

## version.yml

*Manages the release lifecycle.*

1. **`release-please`** — On the main branch, opens or updates the release PR from Conventional Commits, and creates the tag and GitHub release when it merges.

Outputs `new_release_published`, `version` and `tag_name` for the delivery jobs.

## merge.yml

*Dependabot auto-merge.*

1. **`auto-merge`** — For pull requests opened by Dependabot, enables GitHub's auto-merge so the PR merges once required checks pass.

## service.yml

*Orchestrates the full pipeline for backend projects.*

1. Calls → `testing.yml` to validate and build the project.
2. Calls → `merge.yml` to auto-merge Dependabot PRs once testing passes. *(Needs: testing)*
3. Calls → `version.yml` to trigger a release on the main branch. Skip with `enable_versioning: false`. *(Needs: testing)*

Pass `run_tests: false` to skip the test suite. `service.yml`, `library.yml` and `debian.yml` all accept `run_tests` and `enable_versioning`, and `forgepy init` sets them for `--no-testing` and `--no-versioning`.

## library.yml

*Orchestrates PyPI publishing.*

1. Calls → `testing.yml`, `merge.yml` and `version.yml` as above.
2. **`publish`** — On a new release, downloads the build artifact and runs `uv publish` using PyPI Trusted Publishing. Disable with `publish: false`. *(Needs: version)*

Configure the trusted publisher on your PyPI project's settings page first.

## debian.yml

*Orchestrates Debian packaging.*

1. Calls → `testing.yml`, `merge.yml`, `version.yml`, as `service.yml` does.
2. **`build-deb`** — On a new release, builds inside a `debian:bookworm-slim` container so the virtual environment targets the system `python3` the `.deb` depends on, packages it with nfpm, and uploads the `.deb`. *(Needs: version)*

## website.yml

*Orchestrates the full pipeline for website projects and deploys to GitHub Pages.*

1. Calls → `testing.yml` to validate and build the site (`build_command` defaults to `uv run zensical build`). Pass `run_tests: false` for sites without tests.
2. Calls → `merge.yml` to auto-merge Dependabot PRs once testing passes. Disable with `auto_merge: false`. *(Needs: testing)*
3. Calls → `version.yml` to check if a new release was published. Skip with `enable_versioning: false`. *(Needs: testing)*
4. **`deploy`** — Downloads the build artifact and deploys it to GitHub Pages. Runs on the main branch only and, when versioning is enabled, only when a new release is published. *(Needs: testing, version)*

## docker.yml

*Builds a Docker image for any number of platforms and publishes it to GitHub Container Registry.*

`forgepy init --docker` adds it to your `index.yml` as its own `docker` job after your pipeline job, so projects without Docker don't carry it. It builds on every run and pushes when the pipeline reports a new release. The job needs `packages: write` to push.

1. **`prepare`** — Resolves the image name (`ghcr.io/<owner>/<repo>`, lowercased) and turns `platforms` into a build matrix.
2. **`build`** — Builds each platform on its own runner. `linux/amd64` and `linux/arm64` build natively (`ubuntu-24.04-arm`); every other platform is emulated with QEMU. On pull requests the image is built but not pushed, so a broken Dockerfile fails the PR's checks. Make the `docker` job a required status check to stop Dependabot auto-merge on a failing build.
3. **`merge`** — On a new release, combines the per-platform images into one multi-platform manifest tagged `X.Y.Z`, `X.Y`, `X`, `sha-<commit>` and `latest`, with provenance and SBOM attestations. *(Needs: build)*

With `buildkit_endpoint` set, **`build-remote`** replaces `build` and `merge`: one job on `runs_on` builds every platform on that BuildKit, emulating the ones its host can't run natively, and on a release pushes the same tags and attestations itself. The BuildKit host needs QEMU registered for foreign platforms (`binfmt_misc`), and its emulated builds run several times slower than native ones. Pushed images build without the cache, as a shared BuildKit's cache could hold layers another repository's job planted.

| Input | Default | Purpose |
| :--- | :--- | :--- |
| `push` | `false` | Push to GHCR; the generated job sets it for a new release on `main` |
| `version` | `''` | Release version used for the semver tags |
| `image` | `ghcr.io/<owner>/<repo>` | Image name override |
| `platforms` | `linux/amd64,linux/arm64` | Comma-separated platforms, e.g. `linux/amd64,linux/arm64,linux/arm/v7` |
| `buildkit_endpoint` | `''` | A remote BuildKit, e.g. `tcp://runner.builder:1234`, to build every platform in one job on `runs_on` |
| `native_arm` | `true` | Build arm64 on native Arm runners; set `false` to emulate (e.g. if Arm runners aren't available to a private repo) |

The website Dockerfile builds the static site once on the build host and only the nginx stage per target platform. The backend builds entirely per target, because the virtual environment holds platform-specific wheels. Supported platforms follow the base images:

| Image | Platforms |
| :--- | :--- |
| Backend (`python:<version>-slim-bookworm`) | `linux/amd64`, `linux/arm64`, `linux/arm/v7`, `linux/386`, `linux/ppc64le` |
| Website (`nginx:stable-alpine`) | `linux/amd64`, `linux/arm64`, `linux/arm/v6`, `linux/arm/v7`, `linux/386`, `linux/ppc64le`, `linux/riscv64`, `linux/s390x` |
