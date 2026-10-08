"""Checks for Jython 2.7 syntax that vermin can't see.

ruff can't target Python 2, and when it splits a call or a def one argument per line it ends
the list with a comma, even after `*args` or `**kwargs`. Python 3 accepts that comma; Python 2
rejects it as a syntax error, and vermin reads the parsed tree, which doesn't record it.
"""

from __future__ import annotations

import io
import tokenize
from dataclasses import dataclass
from pathlib import Path

from forgepy import console

_IGNORED = {tokenize.NL, tokenize.NEWLINE, tokenize.COMMENT, tokenize.INDENT, tokenize.DEDENT}
_OPENERS = {"(": ")", "[": "]", "{": "}"}


@dataclass
class _Group:
    opener: str
    has_star: bool = False
    at_element_start: bool = True
    last_was_comma: bool = False


def star_trailing_commas(source: str) -> list[int]:
    """Lines whose closing parenthesis follows a comma in a list that has a *args or **kwargs."""
    found: list[int] = []
    stack: list[_Group] = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type in _IGNORED:
            continue
        group = stack[-1] if stack else None
        if token.type == tokenize.OP and token.string in _OPENERS:
            if group is not None:
                group.at_element_start = False
                group.last_was_comma = False
            stack.append(_Group(token.string))
            continue
        if token.type == tokenize.OP and token.string in _OPENERS.values():
            closed = stack.pop() if stack else None
            if closed is not None and closed.opener == "(" and closed.has_star and closed.last_was_comma:
                found.append(token.start[0])
            if stack:
                stack[-1].last_was_comma = False
            continue
        if group is None:
            continue
        if group.at_element_start and token.type == tokenize.OP and token.string in {"*", "**"}:
            group.has_star = True
        is_comma = token.type == tokenize.OP and token.string == ","
        group.at_element_start = is_comma
        group.last_was_comma = is_comma
    return found


def check(paths: list[Path]) -> int:
    files = [f for path in paths for f in (sorted(path.rglob("*.py")) if path.is_dir() else [path])]
    problems = 0
    for file in files:
        try:
            lines = star_trailing_commas(file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, tokenize.TokenError) as exc:
            console.err(f"{file}: {exc}")
            problems += 1
            continue
        for line in lines:
            console.err(f"{file}:{line}: a comma after *args or **kwargs is a syntax error on Jython 2.7")
            problems += 1
    if problems:
        return 1
    console.ok(f"No Python 3-only trailing commas in {len(files)} file(s)")
    return 0
