# Contributing

Thanks for taking a look. This is a small project and I am happy to keep it that
way, but fixes and well-scoped features are welcome.

## Getting set up

```bash
git clone https://github.com/R4SHM1T/metricsmith
cd metricsmith
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Ground rules

- Add a test for anything you change. The suite runs real SQL against SQLite
  and asserts on actual numbers; please keep new tests in that spirit rather
  than only checking the shape of a string.
- Keep the layers separate. Parsing lives in `model.py`, join resolution in
  `graph.py`, SQL generation in `compiler.py`, execution in `runtime.py`. A
  change that blurs those lines will probably be asked to move.
- Generate SQL with sqlglot expressions, not string concatenation.
- If you add a dialect, add it to `_time.py` and cover the grains with tests.

## Reporting bugs

Open an issue with the model YAML, the query, the SQL metricsmith produced
(`compile` prints it), and what you expected. A failing test is the fastest way
to get something fixed.
