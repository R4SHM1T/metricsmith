# metricsmith

A small semantic metrics layer. You define metrics and dimensions once in YAML,
ask for them by name, and metricsmith compiles a single SQL query with the
right joins and runs it. It is a readable take on the idea behind LookML, Cube,
and dbt's MetricFlow, small enough to read in an afternoon.

The point of a metrics layer is that "revenue" should mean one thing. Define it
once, declare how your tables join, and every slice of that number comes from
the same definition instead of a fresh hand-written query that quietly disagrees
with the last one.

```python
from metricsmith import Query, Runtime, SemanticLayer, demo_connection

layer = SemanticLayer.from_dir("examples/semantic")
runtime = Runtime(layer, demo_connection())

result = runtime.run(
    Query(
        metrics=["total_revenue", "paid_revenue"],
        dimensions=["customers.country"],
        order_by=["-total_revenue"],
    )
)
for row in result.rows:
    print(row)
```

```
{'country': 'GB', 'total_revenue': 450.0, 'paid_revenue': 400.0}
{'country': 'FR', 'total_revenue': 360.0, 'paid_revenue': 60.0}
{'country': 'IE', 'total_revenue': 130.0, 'paid_revenue': 90.0}
```

Every result carries the SQL that produced it, so you can always see the query:

```python
print(result.sql)
```

```sql
SELECT
  customers.country AS country,
  SUM(orders.amount) AS total_revenue,
  SUM(CASE WHEN (status = 'paid') THEN orders.amount END) AS paid_revenue
FROM orders
LEFT JOIN customers
  ON orders.customer_id = customers.customer_id
GROUP BY customers.country
ORDER BY total_revenue DESC
```

## Why I built it

I kept running into the same mess on analytics work: three dashboards, three
slightly different definitions of the same metric, and nobody sure which one to
trust. I wanted to understand how a semantic layer actually solves that, so I
built a small one end to end. Parsing the YAML, walking the joins, generating
the SQL with a real expression builder, and proving the output against a known
dataset taught me far more than reading the Cube docs ever did.

metricsmith governs the *output* of an analytics stack: one trusted definition
per metric. Its companion project,
[pactum](https://github.com/R4SHM1T/pactum), guards the *input*: data contracts
that fail your CI build when an upstream table drifts. Contracts in, metrics out.

## Install

Not on PyPI yet. Install from source:

```bash
pip install git+https://github.com/R4SHM1T/metricsmith
```

or clone and install in editable mode:

```bash
git clone https://github.com/R4SHM1T/metricsmith
cd metricsmith
pip install -e ".[dev]"
```

## Defining metrics

A semantic layer is a folder of YAML files, one per model. A model maps to a
table and declares its dimensions, metrics, and joins.

```yaml
name: orders
table: orders
primary_key: order_id

joins:
  - to: customers
    type: many_to_one
    sql: orders.customer_id = customers.customer_id

dimensions:
  - name: status
    type: categorical
  - name: order_date
    sql: created_at
    type: time

metrics:
  - name: total_revenue
    type: sum
    sql: amount
  - name: paid_revenue
    type: sum
    sql: amount
    filters:
      - status = 'paid'
```

Metric types are `count`, `count_distinct`, `sum`, `average`, `min`, and `max`.
Metric `filters` narrow a single metric without touching the rest of the query,
so `total_revenue` and `paid_revenue` can sit in the same result. See
[docs/semantic-layer.md](docs/semantic-layer.md) for the full reference.

## Time grains

Ask a time dimension for a grain with a `__` suffix:

```python
Query(metrics=["total_revenue"], dimensions=["orders.order_date__month"])
```

Grains are `day`, `week`, `month`, `quarter`, and `year`. Weeks start on Monday.
Truncation is generated per SQL dialect.

## Command line

```bash
metricsmith validate examples/semantic
metricsmith metrics  examples/semantic
metricsmith compile  examples/semantic -m total_revenue -d customers.country
metricsmith run      examples/semantic \
    --data orders=examples/data/orders.csv \
    --data customers=examples/data/customers.csv \
    -m total_revenue -d customers.country --order=-total_revenue
```

`compile` prints SQL. `run` executes against a SQLite file (`--db`) or an
in-memory database built from CSVs (`--data table=path`), and prints a table,
JSON, or CSV.

## How it works

```
YAML -> SemanticLayer -> Query -> Compiler (+ join graph) -> SQL -> Runtime -> rows
```

Parsing is pydantic with `extra=forbid` so typos fail loudly. Joins are an
undirected graph walked with BFS. SQL is built with sqlglot expressions rather
than string glue, so the output is parseable and dialect rendering is handled
for you. The runtime just executes and hands back rows. There is a longer write
up in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tests

```bash
pytest -q
```

The suite seeds an in-memory SQLite database from the example CSVs, runs real
queries, and checks the actual totals. A metrics layer that compiles tidy SQL
but returns the wrong number is worse than useless, so the tests check numbers.

## License

MIT. See [LICENSE](LICENSE).
