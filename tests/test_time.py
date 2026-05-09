"""Truncation is generated SQL, so we check it by running it in SQLite."""

import sqlite3

import pytest

from metricsmith import _time


@pytest.fixture
def conn():
    return sqlite3.connect(":memory:")


def _trunc(conn, value, grain):
    expr = _time.truncate("d", grain)
    row = conn.execute(f"SELECT {expr} FROM (SELECT ? AS d)", (value,)).fetchone()
    return row[0]


def test_day(conn):
    assert _trunc(conn, "2026-03-04T10:15:00", "day") == "2026-03-04"


def test_month(conn):
    assert _trunc(conn, "2026-03-04", "month") == "2026-03-01"


def test_year(conn):
    assert _trunc(conn, "2026-03-04", "year") == "2026-01-01"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("2026-02-15", "2026-01-01"),
        ("2026-05-09", "2026-04-01"),
        ("2026-08-01", "2026-07-01"),
        ("2026-11-30", "2026-10-01"),
    ],
)
def test_quarter(conn, value, expected):
    assert _trunc(conn, value, "quarter") == expected


def test_week_lands_on_a_monday(conn):
    # 2026-03-04 is a Wednesday; its week should start Monday 2026-03-02.
    result = _trunc(conn, "2026-03-04", "week")
    assert result == "2026-03-02"
    weekday = conn.execute("SELECT strftime('%w', ?)", (result,)).fetchone()[0]
    assert weekday == "1"


def test_unknown_grain():
    with pytest.raises(ValueError):
        _time.truncate("d", "fortnight")
