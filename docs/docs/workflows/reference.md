---
title: Pipeline reference
description: Stage-by-stage breakdown of each reusable pipeline, and its inputs.
---

# Pipeline reference

This page describes each pipeline's stages and the inputs it takes. For the generated `.index.yml`, when each pipeline runs and the permissions they need, see the [workflows overview](overview.md).

## Choosing runners

Every pipeline takes a `runs_on` input, default `ubuntu-latest`, for each of its jobs. To use self-hosted runners, set it per repository, for example from a repository variable: `runs_on: ${{ vars.RUNS_ON || 'ubuntu-latest' }}`.

`docker.yml`'s builds and its push use GitHub-hosted runners: the arm64 build because it needs a native Arm machine, and the others because they need a Docker daemon. With `buildkit_endpoint` set, it builds every platform in one job on `runs_on` instead, against a remote BuildKit, so self-hosted runners without a Docker daemon can build and push multi-platform images. `debian.yml`'s `build` stays on `ubuntu-latest` too, as it builds inside a Debian container.

## Check pipelines: library.yml, service.yml, website.yml

*Lint, scan, test and build.*

The three share their first four stages, job for job:

1. **`lint`**: `uv sync --locked` (plus `sync_args`), then `ruff check`, `ruff format --check`, `basedpyright`, and `forgepy sync --check` when the project has a `.forgepy/` directory. In a `--jython` project (one with `.forgepy/ruff-jython.toml`) it also runs `poe compat`, the vermin Jython 2.7 check.
2. **`scan`**: Gitleaks secret scan (skip with `enable_secrets: false`) and an OSV-Scanner dependency scan. On a pull request, a high or critical finding (a CVSS score of 7 or more, or GitHub's rating when an advisory has no score) fails the stage, so a change can't add one. Elsewhere, such as on a release, it's an error annotation that doesn't fail it: an advisory published against a dependency you already have shouldn't stop releases, and the weekly `patch` pipeline can upgrade it. Lower findings are warning annotations, and every finding is listed in the job summary. If the scanner can't run, for example because OSV's API is unreachable, the stage warns and passes. To accept a finding you can't fix yet, list it in an [`osv-scanner.toml`](https://google.github.io/osv-scanner/configuration/) beside the lockfile:

    ```toml
    [[IgnoredVulns]]
    id = "GHSA-xxxx-xxxx-xxxx"
    ignoreUntil = 2026-12-31
    reason = "No fixed version yet; the vulnerable function isn't called"
    ```

3. **`test`**: `uv sync --locked` and `pytest` (skip with `run_tests: false`), with the coverage and JUnit reports uploaded as `coverage-<artifact_name>`. *(Needs: lint, scan)*
4. **`build`**: Runs `build_command` (`uv build`, or `uv run zensical build` in `website.yml`) and uploads `dist/` as the `artifact_name` artifact. `library.yml` and `service.yml` skip it with `run_build: false`, which `forgepy init --jython` sets. *(Needs: lint, scan; runs alongside test)*

`website.yml` adds:

5. **`check`**: With `check_links` or `check_accessibility`, checks the uploaded build; see [Site checks](#site-checks). *(Needs: build)*

| Input | Default | Description |
| :--- | :--- | :--- |
| `runs_on` | `'ubuntu-latest'` | Runner label for every job |
| `working_directory` | `'.'` | Directory holding `pyproject.toml` |
| `python_version` | `''` | Python version for every job. Empty reads the project's `.python-version`, and without one uses Python 3.13; see [Python version](../configuration.md#python-version) |
| `enable_secrets` | `true` | Run the Gitleaks secret scan |
| `run_tests` | `true` | Run the test stage; `init --no-testing` sets it to `false` |
| `run_build` | `true` | Run the build stage; `init --jython` sets it to `false`. Not in `website.yml` |
| `sync_args` | `''` | Extra arguments for every `uv sync`, such as `--group` to pick a dependency group |
| `build_command` | `'uv build'` (`'uv run zensical build'` in `website.yml`) | The command the build stage runs; it writes to `dist/` |
| `artifact_name` | `'dist'` | Name of the build artifact, which `publish` and `pages` download. A matrix gives each leg its own |
| `ref` | `''` | Commit, branch or tag to check and build; empty means the commit that triggered the run |
| `pre_build_command` | `''` | Shell command run in `working_directory` before `uv sync`, in every stage that installs |

`website.yml` also takes:

| Input | Default | Description |
| :--- | :--- | :--- |
| `base_path` | `''` | The path the site is served under, such as `/my-repo/` for a GitHub Pages project site; the site checks need it to resolve root-relative links. Empty means `/` |
| `check_links` | `false` | Check the built site's links with lychee; internal links only unless `check_external_links` |
| `check_external_links` | `false` | With `check_links`, check links to other sites too |
| `link_check_args` | `''` | Extra lychee arguments, such as `--include-fragments` or `--exclude <pattern>` |
| `check_accessibility` | `false` | Check the built site against WCAG 2.2 A and AA with axe, in a headless Chromium |
| `accessibility_paths` | `''` | Comma- or newline-separated pages to check, relative to `base_path`; empty checks every page in the sitemap, else the home page |
| `accessibility_impact` | `'serious'` | The lowest axe impact that fails the check (`minor`, `moderate`, `serious` or `critical`); lower ones are warnings |

Each takes one optional secret, `GH_TOKEN`, for `pre_build_command`.

### Building another commit

By default every job checks out the commit that triggered the run. Set `ref` to a branch, tag or commit to check, build and deploy that instead, for example the tip of `main` after an earlier job in the same run pushed a commit to it:

```yaml
jobs:
  generate:
    # ...commits generated files and pushes them to main
  website:
    needs: generate
    uses: apollogeddon/forgepy/.github/workflows/website.yml@main
    with:
      ref: main
```

`library.yml` and `service.yml` take `ref` too.

### Generating content before the build

A site that builds from files something else makes first, such as reference pages a script writes or a file copied from elsewhere in the repository, sets `pre_build_command`. It runs with `bash -e` in `working_directory`, after uv and Python are set up and before `uv sync`, in the lint, test and build stages, so the checks see the same files the build does:

```yaml
jobs:
  website:
    uses: apollogeddon/forgepy/.github/workflows/website.yml@main
    with:
      pre_build_command: |
        uv run --script scripts/gen_reference.py --out docs/reference
        cp CHANGELOG.md docs/changelog.md
    secrets:
      GH_TOKEN: ${{ secrets.DOCS_TOKEN }}
```

The command gets a token, as `GH_TOKEN`, only when the caller passes the `GH_TOKEN` secret; `gh` reads it from there. To give it the run's own token, pass `GH_TOKEN: ${{ github.token }}`; it has the permissions of the calling job. The checkout keeps no credentials, so `git` can't push with it either way.

### Site checks

Two checks of the built site are off by default, as a check that suddenly fails would break the sites already calling `website.yml`. Turn them on with `check_links` and `check_accessibility`. They run in the `check` stage, on the build artifact the `build` stage uploaded, so a failing check stops the deploy and the Dependabot merge but leaves the build to inspect. Each writes its findings to the run's summary. The inputs match forgejs's and forgego's website pipelines.

```yaml
    with:
      base_path: /my-repo/
      check_links: true
      check_accessibility: true
      accessibility_paths: |
        /
        /reference/
```

- **`base_path`** is the path in `site_url` in `mkdocs.yml`, such as `/my-repo/` for `https://owner.github.io/my-repo/`. The stage serves the site under that path, as GitHub Pages does. Leave it empty for a site at the root of its domain, or one with no `site_url`, such as the `mkdocs.yml` `forgepy init --website` writes.
- **`check_links`** runs [lychee](https://github.com/lycheeverse/lychee) over every HTML page, with a directory link needing its `index.html`, and a link without an extension also matching `<path>.html`. With `site_url` set, Zensical writes some links with the site's full address; the stage reads that address from the site's `sitemap.xml` and checks those links in the build as well. It runs `--offline` unless `check_external_links` is on, so another site being down can't fail the check. Pass more lychee options in `link_check_args`, or add a `lychee.toml` or `.lycheeignore` to `working_directory`.
- **`check_accessibility`** serves the site locally and runs [axe](https://github.com/dequelabs/axe-core) in Playwright's headless Chromium against WCAG 2.0, 2.1 and 2.2 A and AA, on each page in `accessibility_paths`, else every page in `sitemap.xml`, else the home page. Zensical lists pages in its sitemap only when `site_url` is set. Violations at `accessibility_impact` or above fail the stage and are annotated on the run; lower ones are reported as warnings. Zensical's default theme fails some `critical` and `serious` rules, such as `button-name` and `aria-required-attr` on its search, so fix those (as this site does in `docs/docs/javascripts/a11y.js`) before turning the check on. A self-hosted runner needs passwordless `sudo`, or Chromium's system libraries already installed.

## version.yml

*release-please.*

1. **`release`**: On `main`, opens or updates the release pull request from Conventional Commits, and creates the tag and GitHub release when it merges. It reads `.github/release.json` and `.github/.release.json` under `working_directory`, so each project in a monorepo is released on its own (see [Projects in a subdirectory](../examples.md#projects-in-a-subdirectory)). When it opened or updated a release pull request, it requests a review on it from `reviewers`, as `merge.yml` does on Dependabot's.

Outputs `new_release_published` (`'true'` or `'false'`), `version` and `tag_name`: those of the `working_directory` package, not of any other package released in the same run.

| Input | Default | Description |
| :--- | :--- | :--- |
| `working_directory` | `'.'` | The package to release |
| `reviewers` | `''` | Comma-separated logins to request a review of the release pull request from; empty means the repository's owner |

### Checking a release

A push to `main` runs `version` first, and only when it makes a release does `.index.yml` run the checks again, and then the publish, image push or deploy that ships what they built. So each change is checked on its pull request and once more as part of a release, not on every push.

release-please tags the release before those checks run. If they fail, the tag and the GitHub release exist with nothing published, and need putting right by hand. The generated `.index.yml` therefore checks release pull requests too, so the release is checked with exactly what its merge ships. release-please opens them with `GITHUB_TOKEN`, which doesn't start workflow runs, so approve the run (or push to the branch) before merging one.

With **Require branches to be up to date before merging** turned on, every pull request is checked again before it merges; skipped jobs count as passed for required status checks.

## publish.yml

*Ships a release.*

1. **`package`**: With `package` (on by default), downloads the build artifact and runs `uv publish` with PyPI [Trusted Publishing](https://docs.pypi.org/trusted-publishers/). Nothing is installed and there's no dependency cache, so no dependency code runs while the job holds its OIDC token. Configure the trusted publisher on your PyPI project first, with `.index.yml` as its workflow.
2. **`assets`**: With `assets` set to an artifact's name, attaches its files to the GitHub release `tag_name` names, replacing any of the same name. The generated `--debian` workflow attaches the `.deb` this way.
3. **`attest`**: With `attest`, attests the build provenance of the published build and the attached files with [`actions/attest-build-provenance`](https://github.com/actions/attest-build-provenance): a signed statement, kept by GitHub, of the repository, commit and workflow run that built them. *(Needs: package, assets)*

Artifact attestations are free in public repositories; a private repository needs GitHub Enterprise Cloud, so `attest` is off by default. To turn it on, grant the `publish` job one more permission:

```yaml
  publish:
    # ...as generated
    with:
      attest: true
    permissions:
      contents: read
      id-token: write
      attestations: write
```

GitHub checks a called workflow's permissions before running any of it, so a caller grants the union of what its jobs ask for, even those turned off. `package`, which holds the publish token, asks for exactly `contents: read` and `id-token: write`, so it never gets `attestations: write` or `contents: write`. `assets` and `attest` ask for none, as asking would stop every caller that doesn't grant them, and take the caller's grant instead.

Outputs `published` (`'true'` when this run published the package).

| Input | Default | Description |
| :--- | :--- | :--- |
| `working_directory` | `'.'` | Directory holding `pyproject.toml` |
| `artifact_name` | `'dist'` | The build artifact to publish |
| `package` | `true` | Publish to PyPI; needs `id-token: write` |
| `assets` | `''` | An artifact whose files to attach to the release; needs `contents: write` |
| `tag_name` | `''` | The release to attach them to, as `version.yml`'s `tag_name` |
| `attest` | `false` | Attest what the other stages shipped; needs `id-token: write` and `attestations: write` |

## pages.yml

*GitHub Pages.*

1. **`deploy`**: Downloads the `artifact_name` build artifact, which `website.yml` uploaded earlier in the run, and deploys it to GitHub Pages. Deploys run one at a time, in the `pages-deploy` concurrency group: a newer deploy waits for a running one, and replaces one still waiting. The group isn't `pages`, the one GitHub's starter Pages workflow uses at workflow level, as a job sharing its caller's group deadlocks.

`forgepy init --website` calls it on a release, or on every push to `main` without versioning.

## debian.yml

*Debian packaging.*

1. **`build`**: Builds inside a `debian:trixie-slim` container, so the virtual environment targets the system `python3` (3.13) the `.deb` depends on, rather than a GitHub-hosted Python at a path no `.deb` dependency can promise. It installs uv with `astral-sh/setup-uv`, as every other job does, and nFPM from a pinned release checked against its SHA-256, runs `packaging/build_deb.py`, and uploads the `.deb` as the `debian-package` artifact.
2. **`test`**: Reads the `.deb` back with `dpkg-deb`: its control fields and file list, so a broken package fails before it ships. *(Needs: build)*

`forgepy init --debian` runs it after `service.yml`'s checks on pull requests and on a release, and on a release attaches the `.deb` to the GitHub release through `publish.yml`'s `assets`. It takes `working_directory` and `runs_on` (for `test`; `build` is a container job on `ubuntu-latest`), and outputs `package_artifact`, the artifact's name.

## docker.yml

*Builds a Docker image for any number of platforms and publishes it to GitHub Container Registry.*

`forgepy init --docker` adds it to `.index.yml` as its own `docker` job after the checks, so projects without Docker don't carry it. It builds on pull requests, so a broken Dockerfile fails the PR's checks and stops a Dependabot merge, and builds and pushes on a release.

1. **`build`**: Builds every platform but a native arm64 one, in one build: `linux/amd64` natively and every other platform with QEMU. When `push` is `true`, it pushes them untagged, by digest.
2. **`build (arm64)`**: With `native_arm` (on by default) and `linux/arm64` in `platforms`, builds arm64 on GitHub's native Arm runner (`ubuntu-24.04-arm`), and pushes it by digest the same way.
3. **`push`**: When `push` is `true`, combines what the builds pushed into one multi-platform manifest tagged `X.Y.Z`, `X.Y`, `X` (omitted for `0.x` versions), `sha-<commit>` and `latest`. *(Needs: build, build (arm64))*

Images carry their provenance (`mode=max`) and SBOM as BuildKit attestations in the image index itself, so they need no `attest` stage; `docker buildx imagetools inspect <image> --format '{{ json .Provenance }}'` shows them.

With `buildkit_endpoint` set, `build` runs on `runs_on` and builds every platform on that BuildKit, emulating the ones its host can't run natively, and on a release pushes the same tags and attestations itself, so `build (arm64)` and `push` are skipped. The BuildKit host needs QEMU registered for foreign platforms (`binfmt_misc`), and its emulated builds run several times slower than native ones. Pushed images build without the cache, as a shared BuildKit's cache could hold layers another repository's job planted.

| Input | Default | Purpose |
| :--- | :--- | :--- |
| `push` | `false` | Push to GHCR; the generated job sets it for a release |
| `version` | `''` | Release version used for the semver tags |
| `image` | `ghcr.io/<owner>/<repo>` | Image name override |
| `platforms` | `linux/amd64,linux/arm64` | Comma-separated platforms, e.g. `linux/amd64,linux/arm64,linux/arm/v7` |
| `native_arm` | `true` | Build arm64 on a native Arm runner; set `false` to emulate (e.g. if Arm runners aren't available to a private repo) |
| `buildkit_endpoint` | `''` | A remote BuildKit, e.g. `tcp://runner.builder:1234`, to build every platform in one job on `runs_on` |
| `working_directory` | `'.'` | Directory holding the Dockerfile |

The website Dockerfile builds the static site once on the build host and only the nginx stage per target platform. The backend builds entirely per target, because the virtual environment holds platform-specific wheels. Supported platforms follow the base images:

| Image | Platforms |
| :--- | :--- |
| Backend (`python:<version>-slim-bookworm`) | `linux/amd64`, `linux/arm64`, `linux/arm/v7`, `linux/386`, `linux/ppc64le` |
| Website (`nginx:stable-alpine`) | `linux/amd64`, `linux/arm64`, `linux/arm/v6`, `linux/arm/v7`, `linux/386`, `linux/ppc64le`, `linux/riscv64`, `linux/s390x` |

## patch.yml

*Managed configs and security patches, weekly, on a manual run and after a Dependabot merge.*

After a Dependabot merge, the `auto-merged` dispatch runs it straight away, so a forgepy bump's refreshed `.forgepy/` lands on `main` without waiting for the week.

1. **`update`**: On `main`, in `working_directory`:
    1. When the project has a `.forgepy/` directory, runs `forgepy sync` and commits any change to it as `chore(deps): refresh the configs forgepy manages`, so a Dependabot bump of forgepy doesn't leave `lint`'s `forgepy sync --check` failing.
    2. Scans `uv.lock` with OSV-Scanner, upgrades only the vulnerable packages with `uv lock --upgrade-package` (transitive ones included, within the ranges `pyproject.toml` allows, without building any package), and commits the new `uv.lock` as `fix(deps): upgrade packages with known vulnerabilities via osv-scanner`. OSV-Scanner can't fix a `uv.lock` in place, so uv does the upgrade.

It checks out the tip of `main`, so a second call in the same run (forgepy patches its docs site after the tool) commits on top of the first. The commits are made with `GITHUB_TOKEN`, so they start no run of their own: release-please picks them up on the next push to `main`.

## merge.yml

*Dependabot's pull requests.*

1. **`review`**: Requests a review from `reviewers`, or from the repository's owner when `reviewers` is empty and the owner is a user (an organisation names its reviewers through the input). GitHub only requests code owners' reviews in a private repository on a paid plan, so without this, Dependabot's pull requests in a private repository on GitHub Free never reach your review requests. It runs whether the checks passed or not, so a failing update reaches you too. A failed request logs a warning and never fails the run.
2. **`squash`**: When `checks_passed` is `true`, and Dependabot both opened the pull request and made its latest change (someone else's push to its branch waits for a person), enables GitHub's auto-merge so the PR merges once required checks pass, or merges it straight away when it can already be merged. It squash-merges, so release-please lists each update once: a merge commit repeats the pull request's title, and release-please reads that as a second change. Merge your own pull requests the same way, with **Squash and merge**. GitHub Actions updates (branches starting `dependabot/github_actions/`) are left for a person to merge: they change workflow files, which `GITHUB_TOKEN` can't merge. Once the pull request has merged, it sends the `auto-merged` `repository_dispatch` event, so `.index.yml` runs on `main`: a merge made with `GITHUB_TOKEN` starts no push run. When it enabled auto-merge rather than merging, it waits up to 12 minutes for the merge before sending it. See [Secrets](overview.md#secrets).

The generated `merge` job passes `checks_passed` as whether every check job before it passed.

| Input | Default | Description |
| :--- | :--- | :--- |
| `reviewers` | `''` | Comma-separated logins to request a review from; empty means the repository's owner |
| `checks_passed` | `false` | Whether the pull request's checks passed in this run; `squash` only runs when they did |

## Inputs that moved

Earlier releases' `library.yml`, `service.yml`, `website.yml` and `debian.yml` each ran a whole pipeline: checks, review requests, the Dependabot merge, release-please, security patches and delivery. Each is now one part, and `.index.yml` decides when each part runs, so a hand-written caller moves these inputs:

| Old input | Now |
| :--- | :--- |
| `test_on_push`, `test_release_prs` | Gone: the root job's `if` decides (see [Checking a release](#checking-a-release)) |
| `enable_versioning` | Gone: call `version.yml`, or leave it out |
| `auto_patch` | Gone: call `patch.yml` on the schedule, a manual run and the `auto-merged` dispatch |
| `publish` (`library.yml`) | Gone: call `publish.yml` |
| `reviewers` | `version.yml`'s and `merge.yml`'s `reviewers` |
| `auto_merge` (`website.yml`) | Gone: call `merge.yml` once per run |
| `run_tests`, `enable_secrets`, `python_version`, `working_directory`, `artifact_name`, `runs_on` | Unchanged, on the check pipelines |
| `run_build`, `sync_args` | Unchanged on `service.yml`, and now on `library.yml` too |
| `build_command` | Unchanged on `website.yml`, and now on `library.yml` and `service.yml` too |
| `ref`, `pre_build_command`, `GH_TOKEN` | Unchanged on `website.yml`, and now on `library.yml` and `service.yml` too |
| `debian.yml`'s check inputs | Pass them to `service.yml`; `debian.yml` takes `working_directory` and `runs_on` |

| Old output | Now |
| :--- | :--- |
| `new_release_published`, `version`, `tag_name` (`service.yml`, `website.yml`, `debian.yml`) | `version.yml`'s |

`testing.yml`, `quality.yml` and `review.yml` are gone: their jobs are the check pipelines' stages, `patch.yml`'s `update`, and `merge.yml`'s and `version.yml`'s review requests. A caller of `testing.yml`, such as a matrix over dependency groups, calls `library.yml` or `service.yml` with the same inputs, less `auto_patch`; see [Checking against several dependency groups](../examples.md#checking-against-several-dependency-groups).
