# Security Policy

## Supported Versions

Only the latest published version of `forgepy` receives security fixes.

## Reporting a Vulnerability

Please report security vulnerabilities privately using [GitHub's private vulnerability reporting](https://github.com/Apollogeddon/forgepy/security/advisories/new) rather than opening a public issue.

You should expect an initial response within a few days. If the issue is confirmed, a fix will be released as a patch version and credited in the advisory unless you request otherwise.

## Automated Security Tooling

This repository runs the following on every change:

- **Gitleaks** — scans for committed secrets
- **OSV-Scanner** — scans dependencies for known vulnerabilities
- **Dependabot** — with a 3-day cooldown before new dependency versions are proposed, giving time for a compromised release to be caught and yanked upstream
