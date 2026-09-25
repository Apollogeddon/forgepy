from __future__ import annotations

import argparse
import sys
from pathlib import Path

from forgepy import __version__, console
from forgepy.config import InitConfig, Mode
from forgepy.core import init


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="forgepy", description="Quality control CLI for Python projects")
    parser.add_argument("-V", "--version", action="version", version=f"forgepy {__version__}")

    subparsers = parser.add_subparsers(dest="command")
    init_parser = subparsers.add_parser("init", help="Initialize a Python project with forgepy conventions")

    mode_group = init_parser.add_mutually_exclusive_group()
    mode_group.add_argument("--backend", action="store_const", dest="mode", const=Mode.BACKEND)
    mode_group.add_argument("--library", action="store_const", dest="mode", const=Mode.LIBRARY)
    mode_group.add_argument("--website", action="store_const", dest="mode", const=Mode.WEBSITE)
    init_parser.set_defaults(mode=None)

    init_parser.add_argument("--all", action=argparse.BooleanOptionalAction, default=None)
    init_parser.add_argument("--testing", action=argparse.BooleanOptionalAction, default=None)
    init_parser.add_argument("--linting", action=argparse.BooleanOptionalAction, default=None)
    init_parser.add_argument("--versioning", action=argparse.BooleanOptionalAction, default=None)

    init_parser.add_argument("--docker", action="store_true")
    init_parser.add_argument("--debian", action="store_true")

    init_parser.add_argument("--force", action="store_true")
    init_parser.add_argument("--dry-run", action="store_true")
    init_parser.add_argument("--python", dest="python_version", default="3.13")
    init_parser.add_argument("-C", "--path", dest="path", default=".")

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
