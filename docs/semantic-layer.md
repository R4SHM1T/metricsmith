# Defining a semantic layer

A semantic layer is a folder of YAML files, one per model. Each model maps to a
table and declares its dimensions, metrics, and joins.

## A model file

```yaml
name: orders          # how queries refer to this model
table: orders         # the physical table name
primary_key: order_id
description: One row per customer order.

joins:
  - to: customers
    type: many_to_one
    sql: orders.customer_id = customers.customer_id

dimensions:
  - name: status
    type: categorical
  - name: order_date
    sql: created_at     # column differs from the dimension name
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

## Dimensions

A dimension is something you group by. If `sql` is omitted it defaults to a
column with the same name as the dimension. Types are `categorical`, `time`,
`boolean`, and `numeric`.

Time dimensions can be asked for at a grain using a `__` suffix:

```
order_date__day
order_date__week     # weeks start on Monday
order_date__month
order_date__quarter
order_date__year
```

## Metrics

A metric is an aggregation. Supported types are `count`, `count_distinct`,
`sum`, `average`, `min`, and `max`. Every type except `count` needs a `sql`
expression to aggregate.

Metric `filters` narrow what the metric counts without affecting anything else
in the query. `paid_revenue` above sums `amount` only for paid orders, so you
can put `total_revenue` and `paid_revenue` side by side in the same result.

## Joins

Declare a join once, on either side. metricsmith treats joins as undirected and
works out the path between models when a query spans more than one. All joins
are emitted as LEFT JOIN so the base table keeps its grain.

## Referring to metrics and dimensions

Metric names are unique across the whole layer, so `total_revenue` is enough.
Dimensions can be written bare (`country`) when unambiguous, or qualified
(`customers.country`) when the same name exists on more than one model.

## Querying

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
print(result.sql)   # the exact SQL that ran
```
