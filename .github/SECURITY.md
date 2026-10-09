# Security policy

## Supported versions

Only the latest release of Forge.py receives security fixes.

## Reporting a vulnerability

Report vulnerabilities privately through [GitHub's private vulnerability reporting](https://github.com/Apollogeddon/forgepy/security/advisories/new). Don't open a public issue.

You can expect a first response within a few days. If the issue is confirmed, the fix is released as a patch version and credited in the advisory unless you ask otherwise.

## Automated security tooling

This repository uses:

- **Gitleaks**, which scans each change for committed secrets.
- **OSV-Scanner**, which scans the dependencies for known vulnerabilities on each change.
- **Dependabot**, which proposes dependency and GitHub Actions updates. It waits three days after a version is published before proposing it, so a compromised release has time to be caught and yanked upstream.
