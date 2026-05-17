"""Command line interface for metricsmith.

    metricsmith validate <dir>
    metricsmith metrics  <dir>
    metricsmith compile  <dir> -m total_revenue -d customers.country
    metricsmith run      <dir> --data orders=orders.csv --data customers=customers.csv \\
                          -m total_revenue -d customers.country --order=-total_revenue

`compile` prints the SQL. `run` executes it against a SQLite database (either
an existing file via --db, or one built on the fly from --data CSVs) and prints
the result. Exit code is 0 on success, 1 on any handled error.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from typing import List, Optional

from .errors import MetricsmithError
from .model import SemanticLayer
from .query import Query
from .runtime import Runtime
from .seed import load_csv_tables


def _add_query_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("directory", help="folder of semantic model files (*.yml)")
    parser.add_argument(
        "-m", "--metric", action="append", default=[], dest="metrics",
        help="metric to select (repeatable)",
    )
    parser.add_argument(
        "-d", "--dimension", action="append", default=[], dest="dimensions",
        help="dimension to group by (repeatable)",
    )
    parser.add_argument(
        "-f", "--filter", action="append", default=[], dest="filters",
        help="SQL filter condition (repeatable)",
    )
    parser.add_argument(
        "-o", "--order", action="append", default=[], dest="order_by",
        help="order by a selected name; prefix with '-' for descending. "
             "For a descending value pass it glued, e.g. --order=-total_revenue",
    )
    parser.add_argument("-l", "--limit", type=int, default=None)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metricsmith", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="load and check a semantic layer")
    validate.add_argument("directory")

    metrics = sub.add_parser("metrics", help="list metrics and dimensions")
    metrics.add_argument("directory")

    compile_p = sub.add_parser("compile", help="print the SQL for a query")
    _add_query_args(compile_p)

    run_p = sub.add_parser("run", help="execute a query and print the result")
    _add_query_args(run_p)
    run_p.add_argument("--db", default=None, help="path to a SQLite database file")
    run_p.add_argument(
        "--data", action="append", default=[], metavar="TABLE=CSV",
        help="load a CSV into an in-memory table (repeatable)",
    )
    run_p.add_argument(
        "--format", choices=["table", "json", "csv"], default="table",
    )
    return parser


def _query_from_args(args: argparse.Namespace) -> Query:
    return Query(
        metrics=args.metrics,
        dimensions=args.dimensions,
        filters=args.filters,
        order_by=args.order_by,
        limit=args.limit,
    )


def _connection(args: argparse.Namespace) -> sqlite3.Connection:
    if args.db:
        return sqlite3.connect(args.db)
    connection = sqlite3.connect(":memory:")
    if args.data:
        mapping = {}
        for item in args.data:
            if "=" not in item:
                raise MetricsmithError(f"--data expects TABLE=CSV, got '{item}'")
            table, path = item.split("=", 1)
            mapping[table] = path
        load_csv_tables(connection, mapping)
    return connection


def _print_table(columns: List[str], rows: List[dict]) -> None:
    if not rows:
        print("(no rows)")
        return
    widths = {c: len(c) for c in columns}
    rendered = []
    for row in rows:
        cells = {c: _cell(row.get(c)) for c in columns}
        for c in columns:
            widths[c] = max(widths[c], len(cells[c]))
        rendered.append(cells)
    header = "  ".join(c.ljust(widths[c]) for c in columns)
    print(header)
    print("  ".join("-" * widths[c] for c in columns))
    for cells in rendered:
        print("  ".join(cells[c].ljust(widths[c]) for c in columns))


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text if text else "0"
    return str(value)


def _print_csv(columns: List[str], rows: List[dict]) -> None:
    import csv

    writer = csv.writer(sys.stdout)
    writer.writerow(columns)
    for row in rows:
        writer.writerow([row.get(c) for c in columns])


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            layer = SemanticLayer.from_dir(args.directory)
            print(
                f"ok: {len(layer.models)} model(s), "
                f"{len(layer.all_metrics())} metric(s), "
                f"{len(layer.all_dimensions())} dimension(s)"
            )
            return 0

        if args.command == "metrics":
            layer = SemanticLayer.from_dir(args.directory)
            print("Metrics:")
            for model_name, metric in layer.all_metrics():
                suffix = f"  {metric.description}" if metric.description else ""
                print(f"  {metric.name}  ({model_name}.{metric.type}){suffix}")
            print("Dimensions:")
            for model_name, dim in layer.all_dimensions():
                print(f"  {model_name}.{dim.name}  ({dim.type})")
            return 0

        if args.command == "compile":
            layer = SemanticLayer.from_dir(args.directory)
            compiled = Runtime(layer, None).compile(_query_from_args(args))
            print(compiled.sql)
            return 0

        if args.command == "run":
            layer = SemanticLayer.from_dir(args.directory)
            connection = _connection(args)
            result = Runtime(layer, connection).run(_query_from_args(args))
            if args.format == "json":
                print(json.dumps(result.rows, indent=2, default=str))
            elif args.format == "csv":
                _print_csv(result.columns, result.rows)
            else:
                _print_table(result.columns, result.rows)
            return 0
    except MetricsmithError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    parser.error("unknown command")
    return 2
