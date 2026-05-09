"""End to end: compile, run against SQLite, check the numbers are right."""

from metricsmith import Query


def _by(rows, key, value):
    return next(r for r in rows if r[key] == value)


def test_revenue_by_country(runtime):
    result = runtime.run(
        Query(
            metrics=["total_revenue", "paid_revenue", "order_count"],
            dimensions=["customers.country"],
            order_by=["-total_revenue"],
        )
    )
    rows = result.rows
    assert [r["country"] for r in rows] == ["GB", "FR", "IE"]

    gb = _by(rows, "country", "GB")
    assert gb["total_revenue"] == 450
    assert gb["paid_revenue"] == 400
    assert gb["order_count"] == 4

    ie = _by(rows, "country", "IE")
    assert ie["total_revenue"] == 130
    assert ie["paid_revenue"] == 90
    assert ie["order_count"] == 2


def test_grand_totals(runtime):
    result = runtime.run(
        Query(metrics=["total_revenue", "paid_revenue", "order_count"])
    )
    assert len(result) == 1
    row = result.rows[0]
    assert row["total_revenue"] == 940
    assert row["paid_revenue"] == 550
    assert row["order_count"] == 8


def test_revenue_by_month(runtime):
    result = runtime.run(
        Query(
            metrics=["total_revenue"],
            dimensions=["orders.order_date__month"],
            order_by=["order_date_month"],
        )
    )
    got = {r["order_date_month"]: r["total_revenue"] for r in result.rows}
    assert got == {
        "2026-03-01": 250,
        "2026-04-01": 330,
        "2026-05-01": 360,
    }


def test_distinct_customers_by_country(runtime):
    result = runtime.run(
        Query(metrics=["customer_count"], dimensions=["customers.country"])
    )
    got = {r["country"]: r["customer_count"] for r in result.rows}
    assert got == {"GB": 2, "IE": 1, "FR": 2}


def test_avg_order_value(runtime):
    result = runtime.run(Query(metrics=["avg_order_value"]))
    assert round(result.rows[0]["avg_order_value"], 2) == 117.5


def test_query_filter_is_applied(runtime):
    result = runtime.run(
        Query(metrics=["order_count"], filters=["status != 'cancelled'"])
    )
    assert result.rows[0]["order_count"] == 7
