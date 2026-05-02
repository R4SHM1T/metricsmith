import pytest

from metricsmith import MetricSpec, ModelError, ModelSpec, SemanticLayer


def test_loads_example_layer(layer):
    assert set(layer.models) == {"orders", "customers"}
    model, metric = layer.metric("total_revenue")
    assert model.name == "orders"
    assert metric.type == "sum"


def test_dimension_resolution(layer):
    model, dim, grain = layer.dimension("customers.country")
    assert model.name == "customers" and dim.name == "country" and grain is None


def test_time_grain_parsed(layer):
    model, dim, grain = layer.dimension("orders.order_date__month")
    assert dim.type == "time" and grain == "month"


def test_grain_on_non_time_is_rejected(layer):
    with pytest.raises(ModelError):
        layer.dimension("orders.status__month")


def test_unknown_metric_raises(layer):
    with pytest.raises(ModelError):
        layer.metric("nonsense")


def test_duplicate_metric_names_rejected():
    a = ModelSpec.from_dict(
        {"name": "a", "table": "a", "metrics": [{"name": "rev", "type": "sum", "sql": "x"}]}
    )
    b = ModelSpec.from_dict(
        {"name": "b", "table": "b", "metrics": [{"name": "rev", "type": "sum", "sql": "y"}]}
    )
    with pytest.raises(ModelError):
        SemanticLayer([a, b])


def test_sum_metric_requires_sql():
    with pytest.raises(Exception):
        MetricSpec(name="bad", type="sum")


def test_unknown_key_is_rejected():
    with pytest.raises(ModelError):
        ModelSpec.from_dict({"name": "a", "table": "a", "colour": "blue"})


def test_join_to_unknown_model_rejected():
    spec = ModelSpec.from_dict(
        {
            "name": "a",
            "table": "a",
            "joins": [{"to": "ghost", "sql": "a.id = ghost.id"}],
        }
    )
    with pytest.raises(ModelError):
        SemanticLayer([spec])
