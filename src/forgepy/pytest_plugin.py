from __future__ import annotations

import pytest

EXIT_NO_TESTS_COLLECTED = 5


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addini(
        "forgepy_pass_with_no_tests",
        help="Treat 'no tests collected' as success instead of failure",
        type="bool",
        default=False,
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if exitstatus != EXIT_NO_TESTS_COLLECTED:
        return
    if session.config.getini("forgepy_pass_with_no_tests"):
        session.exitstatus = 0
