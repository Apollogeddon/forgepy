from __future__ import annotations

import argparse
import sys
from pathlib import Path

from forgepy import __version__, console
from forgepy.config import InitConfig, Mode
from forgepy.core import init
from forgepy.sync import sync


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="forgepy",
        description="Scaffolds best-practice tooling into Python projects: linting, type-checking, "
        "testing, CI/CD, Docker, and Debian packaging.",
    )
    parser.add_argument("-V", "--version", action="version", version=f"forgepy {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize a Python project with forgepy conventions",
        description="Scaffold tooling into the current (or target) project. Safe to re-run: "
        "existing files are left alone unless --force is passed.",
    )

    mode_group = init_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--backend", action="store_const", dest="mode", const=Mode.BACKEND, help="Service/application (default)"
    )
    mode_group.add_argument(
        "--library", action="store_const", dest="mode", const=Mode.LIBRARY, help="Publishable PyPI package"
    )
    mode_group.add_argument(
        "--website", action="store_const", dest="mode", const=Mode.WEBSITE, help="Static docs site (mkdocs)"
    )
    init_parser.set_defaults(mode=None)

    init_parser.add_argument(
        "--all", action=argparse.BooleanOptionalAction, default=None, help="Enable/disable every standard feature"
    )
    init_parser.add_argument(
        "--testing", action=argparse.BooleanOptionalAction, default=None, help="pytest + coverage (default: on)"
    )
    init_parser.add_argument(
        "--linting",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="ruff + basedpyright + pre-commit (default: on)",
    )
    init_parser.add_argument(
        "--versioning",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="release-please + commitizen (default: on)",
    )

    init_parser.add_argument("--docker", action="store_true", help="Add a Dockerfile (not available for --library)")
    init_parser.add_argument("--debian", action="store_true", help="Add nfpm-based .deb packaging (--backend only)")

    init_parser.add_argument("--force", action="store_true", help="Overwrite existing config files")
    init_parser.add_argument("--dry-run", action="store_true", help="Show what would change without writing")
    init_parser.add_argument(
        "--python",
        dest="python_version",
        default="3.13",
        metavar="VERSION",
        help="Target Python version (default: 3.13)",
    )
    init_parser.add_argument(
        "-C", "--path", dest="path", default=".", metavar="DIR", help="Target directory (default: current directory)"
    )

    sync_parser = subparsers.add_parser(
        "sync",
        help="Refresh forgepy's managed .forgepy/ base configs",
        description="Refresh the vendored ruff/basedpyright base configs under .forgepy/ "
        "against the version of forgepy currently installed.",
    )
    sync_parser.add_argument("--check", action="store_true", help="Report drift without writing (exit 1 if found)")
    sync_parser.add_argument(
        "-C", "--path", dest="path", default=".", metavar="DIR", help="Target directory (default: current directory)"
    )

    return parser


def _resolve(flag: bool | None, all_value: bool | None) -> bool:
    if flag is not None:
        return flag
    return all_value if all_value is not None else True


def main(argv: list[str] | None = None) -> int:
    console.setup_stdio()
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    if args.command == "sync":
        return sync(Path(args.path).resolve(), check=args.check)

    cfg = InitConfig(
        mode=args.mode or Mode.BACKEND,
        force=args.force,
        dry_run=args.dry_run,
        testing=_resolve(args.testing, args.all),
        linting=_resolve(args.linting, args.all),
        versioning=_resolve(args.versioning, args.all),
        docker=args.docker,
        debian=args.debian,
        python_version=args.python_version,
        target=Path(args.path).resolve(),
    )

    errors = cfg.validate()
    if errors:
        for error in errors:
            console.err(error)
        return 2

    return init(cfg)


if __name__ == "__main__":
    sys.exit(main())
