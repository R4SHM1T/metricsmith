"""Run a few metricsmith queries against the example data.

    python examples/quickstart.py

Nothing here is mocked: the numbers come straight out of SQLite running the
SQL that metricsmith compiled.
"""

from pathlib import Path

from metricsmith import Query, Runtime, SemanticLayer, demo_connection

HERE = Path(__file__).resolve().parent


def main() -> None:
    layer = SemanticLayer.from_dir(str(HERE / "semantic"))
    runtime = Runtime(layer, demo_connection())

    print("Revenue by country\n")
    result = runtime.run(
        Query(
            metrics=["total_revenue", "paid_revenue", "order_count"],
            dimensions=["customers.country"],
            order_by=["-total_revenue"],
        )
    )
    _show(result)

    print("\nThe SQL metricsmith generated:\n")
    print(result.sql)

    print("\nRevenue by month\n")
    _show(
        runtime.run(
            Query(
                metrics=["total_revenue"],
                dimensions=["orders.order_date__month"],
                order_by=["order_date_month"],
            )
        )
    )


def _show(result) -> None:
    print("  ".join(result.columns))
    for row in result.rows:
        print("  ".join(str(row[c]) for c in result.columns))


if __name__ == "__main__":
    main()
