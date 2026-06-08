# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/), and the project aims to follow
semantic versioning.

## [0.2.0] - 2026-06-08

### Added
- Time-grain dimensions (`day`, `week`, `month`, `quarter`, `year`) via a
  `__grain` suffix, compiled per dialect.
- `count_distinct` metric type.
- Query-level `filters`, `order_by`, and `limit`.
- CLI `validate`, `metrics`, `compile`, and `run` subcommands with table, JSON,
  and CSV output.

### Changed
- Joins are now resolved as an undirected graph, so a join declared on one side
  is usable from the other.
- Metric filters compile to CASE expressions for broad SQLite compatibility.

## [0.1.0] - 2026-04-19

### Added
- First cut: model/metric/dimension definitions in YAML, a single-table
  compiler, and a SQLite runtime.
