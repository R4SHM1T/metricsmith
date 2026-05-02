import pytest

from metricsmith import Compiler, Query, QueryError


def _sql(layer, query):
    return Compiler(layer).compile(query).sql.lower()


def test_simple_aggregate_has_no_group_by(layer):
    compiled = Compiler(layer).compile(Query(metrics=["total_revenue"]))
    assert "group by" not in compiled.sql.lower()
    assert "sum(" in compiled.sql.lower()
    assert compiled.metrics == ["total_revenue"]


def test_grouping_adds_group_by_and_alias(layer):
    compiled = Compiler(layer).compile(
        Query(metrics=["order_count"], dimensions=["orders.status"])
    )
    sql = compiled.sql.lower()
    assert "group by" in sql
    assert " as status" in sql
    assert "count(*)" in sql
    assert compiled.dimensions == ["status"]


def test_cross_model_query_emits_join(layer):
    sql = _sql(
        layer,
        Query(metrics=["total_revenue"], dimensions=["customers.country"]),
    )
    assert "join" in sql
    assert "customers" in sql and "orders" in sql


def test_filtered_metric_becomes_case(layer):
    sql = _sql(layer, Query(metrics=["paid_revenue"]))
    assert "case when" in sql
    assert "paid" in sql


def test_time_grain_truncates(layer):
    sql = _sql(
        layer,
        Query(metrics=["total_revenue"], dimensions=["orders.order_date__month"]),
    )
    assert "strftime" in sql
    assert "order_date_month" in sql


def test_order_and_limit(layer):
    sql = _sql(
        layer,
        Query(
            metrics=["total_revenue"],
            dimensions=["customers.country"],
            order_by=["-total_revenue"],
            limit=2,
        ),
    )
    assert "order by" in sql and "desc" in sql
    assert "limit 2" in sql


def test_order_by_unknown_name_raises(layer):
    with pytest.raises(QueryError):
        Compiler(layer).compile(
            Query(metrics=["total_revenue"], order_by=["made_up"])
        )
