from __future__ import annotations

from pathlib import Path

import pytest

from forgepy.jython import check, star_trailing_commas

EXPLODED_DEF = "def handler(\n    event,\n    *args,\n    **kwargs,\n):\n    pass\n"


@pytest.mark.parametrize(
    ("source", "lines"),
    [
        (EXPLODED_DEF, [5]),
        ("handler(\n    event,\n    *args,\n)\n", [4]),
        ("handler(event, **{'k': 1},)\n", [1]),
        ("handler(\n    event,  # first\n    **kwargs,  # last\n)\n", [4]),
    ],
)
def test_finds_a_comma_after_star_arguments(source: str, lines: list[int]):
    assert star_trailing_commas(source) == lines


@pytest.mark.parametrize(
    "source",
    [
        "handler(event, *args, **kwargs)\n",
        "handler(\n    event,\n    context,\n)\n",
        "def handler(event, context,):\n    pass\n",
        "handler((a, b,), *args)\n",
        "handler(wrap(*args), event,)\n",
        "handler(a * b, c,)\n",
        "values = [first, second,]\n",
    ],
)
def test_allows_what_python_2_allows(source: str):
    assert star_trailing_commas(source) == []


def test_check_reports_each_file(tmp_path: Path):
    (tmp_path / "good.py").write_text("handler(event, *args)\n", encoding="utf-8")
    assert check([tmp_path]) == 0
    (tmp_path / "bad.py").write_text(EXPLODED_DEF, encoding="utf-8")
    assert check([tmp_path]) == 1
