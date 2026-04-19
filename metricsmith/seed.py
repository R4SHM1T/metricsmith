"""Load CSV files into a SQLite database.

Useful for the examples, the tests, and for kicking the tyres on a real
semantic layer without standing up a warehouse. `demo_connection` builds an
in-memory database from the CSVs shipped in examples/data.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict

import pandas as pd


def load_csv_tables(connection: sqlite3.Connection, tables: Dict[str, str]) -> None:
    """Load ``{table_name: csv_path}`` into the connection, replacing tables."""
    for table, path in tables.items():
        frame = pd.read_csv(path)
        frame.to_sql(table, connection, if_exists="replace", index=False)


def _examples_data() -> Path:
    return Path(__file__).resolve().parent.parent / "examples" / "data"


def demo_connection() -> sqlite3.Connection:
    """An in-memory SQLite DB loaded with the example orders and customers."""
    data = _examples_data()
    connection = sqlite3.connect(":memory:")
    load_csv_tables(
        connection,
        {
            "orders": str(data / "orders.csv"),
            "customers": str(data / "customers.csv"),
        },
    )
    return connection
