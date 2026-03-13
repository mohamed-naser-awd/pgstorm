# pgstorm Documentation

A lightweight PostgreSQL query builder and ORM for Python. This documentation covers installation, models, the QuerySet API, engine configuration, SQL functions, and subqueries.

## Contents

- **[Installation & Setup](installation.md)** — Requirements, install, connection strings, minimal setup
- **[Models & Types](models.md)** — Defining models, scalar types, relations (ForeignKey, OneToOne, ManyToMany)
- **[QuerySet API](queryset.md)** — Filtering, Q objects, joins, aggregates, annotate, alias, column selection
- **[Engine & Execution](engine.md)** — create_engine, sync/async interfaces, transactions, fetching results
- **[Functions & Aggregates](functions.md)** — SQL functions (Concat, Upper, Now, etc.), aggregates (Min, Max, Count, Sum, Avg)
- **[Subqueries](subqueries.md)** — Subquery, OuterRef, correlated subqueries, CTEs
- **[API Reference](api-reference.md)** — Full reference for classes, functions, and methods
 - **[Observers & hooks](observers.md)** — Registering callbacks around queries, connections, and transactions

## Quick Links

- [Main README](../README.md) — Project overview and quick start
- [Example models](../example/model.py) — Sample model definitions
