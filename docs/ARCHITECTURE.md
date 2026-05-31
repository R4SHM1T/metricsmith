# Architecture

metricsmith turns a set of YAML model files into SQL you can run. The pipeline
is small and each stage has one job, which makes the whole thing easy to read
and to test.

```
YAML files
   |  model.py  (pydantic, extra=forbid)
   v
SemanticLayer  -- models, dimensions, metrics, joins; name indexes
   |  query.py
   v
Query          -- what you asked for: metrics, dimensions, filters, order, limit
   |  graph.py    (BFS over joins)         compiler.py (sqlglot)
   v
CompiledQuery  -- a single GROUP BY statement plus its column aliases
   |  runtime.py  (DB-API execute)
   v
QueryResult    -- rows as dicts, and the SQL that produced them
```

## Why a semantic layer

The same number gets computed a dozen different ways across a company:
"revenue" in one dashboard filters out refunds, another forgets to. A semantic
layer is the fix: define `total_revenue` once, declare how `orders` joins to
`customers`, and every slice of that metric is derived from the one definition.
This is the idea behind LookML, Cube, and dbt's MetricFlow. metricsmith is a
small, readable take on the same pattern.

## The pieces

### model.py

Models are validated with pydantic and `extra=forbid`. A misspelled key is an
error at load time, not a rule that quietly never runs. A `SemanticLayer`
indexes metrics by name and enforces that metric names are globally unique, so
a query can ask for `total_revenue` without naming the model it lives on.

The model field is called `name` rather than `model` on purpose: pydantic
reserves the `model_` namespace, and fighting that just to save four letters is
not worth it.

### graph.py

Joins form an undirected graph. When a query touches more than one model the
graph finds the shortest path between them with breadth-first search and emits
one LEFT JOIN per hop. LEFT keeps the grain of the base table intact, which is
the behaviour you almost always want when attaching dimensions to a fact table.

### compiler.py

The compiler resolves the query against the layer, decides which tables are
needed, and builds the statement with sqlglot's expression builder instead of
string concatenation. Building real expressions means the output is parseable
and the dialect rendering is sqlglot's problem, not ours.

Metric filters compile to `SUM(CASE WHEN ... THEN x END)` rather than the SQL
standard `FILTER (WHERE ...)` clause, because the CASE form runs on every
SQLite build people actually have installed.

### runtime.py

The runtime is intentionally boring: compile, execute against a DB-API
connection, return rows as dictionaries with the SQL attached. Carrying the SQL
on the result matters; being able to show the query is half of trusting the
number.

## Time grains

Time dimensions can be requested at a grain with a `__` suffix, for example
`orders.order_date__month`. Truncation is generated per dialect in `_time.py`.
The SQLite path leans on `strftime` and date arithmetic; other dialects get a
standard `DATE_TRUNC`. Week starts on Monday.

## Testing

The tests run real queries against an in-memory SQLite database seeded from the
example CSVs and assert on concrete totals. That is deliberate: a metrics layer
that compiles clean SQL but returns the wrong number is worse than useless, so
the suite checks the numbers, not just the shape of the SQL.
