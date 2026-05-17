import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from metricsmith.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
SEMANTIC = str(EXAMPLES / "semantic")
ORDERS = str(EXAMPLES / "data" / "orders.csv")
CUSTOMERS = str(EXAMPLES / "data" / "customers.csv")


def _run(args):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = main(args)
    return code, buf.getvalue()


def test_validate_ok():
    code, out = _run(["validate", SEMANTIC])
    assert code == 0 and "ok:" in out


def test_metrics_lists_names():
    code, out = _run(["metrics", SEMANTIC])
    assert code == 0
    assert "total_revenue" in out and "country" in out


def test_compile_prints_sql():
    code, out = _run(
        ["compile", SEMANTIC, "-m", "total_revenue", "-d", "customers.country"]
    )
    assert code == 0
    assert "JOIN" in out.upper() and "GROUP BY" in out.upper()


def test_run_table_output():
    code, out = _run(
        [
            "run", SEMANTIC,
            "--data", f"orders={ORDERS}",
            "--data", f"customers={CUSTOMERS}",
            "-m", "total_revenue", "-d", "customers.country",
            "--order=-total_revenue",
        ]
    )
    assert code == 0
    assert "GB" in out and "450" in out


def test_run_json_output():
    code, out = _run(
        [
            "run", SEMANTIC,
            "--data", f"orders={ORDERS}",
            "--data", f"customers={CUSTOMERS}",
            "-m", "order_count",
            "--format", "json",
        ]
    )
    assert code == 0
    payload = json.loads(out)
    assert payload[0]["order_count"] == 8


def test_unknown_metric_exits_nonzero():
    code, _ = _run(["compile", SEMANTIC, "-m", "ghost"])
    assert code == 1
