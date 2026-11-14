# engineering-ops-db

Relational operational ledger and budget reporting tool built with **Python 3.12** and **SQLite 3** (`sqlite3`). It models an engineering organisation's departments, staff, cloud services, operational incidents, and transactional audit logs using a third-normal-form (3NF) schema.

## Schema & Design

- **Database constraints**: Enforces foreign keys (`PRAGMA foreign_keys = ON`), `CHECK` constraints for non-negative budgets/salaries and resolution durations, and indexed lookup columns (`emp_code`, `service_code`, `audit_log` timestamps).
- **Pre-aggregated CTE reporting**: `get_department_budget_summary()` aggregates employee payroll and annualised cloud infrastructure spend in separate Common Table Expressions before joining against `departments`, avoiding row multiplication in financial totals.
- **Transactional audit logging**: Schema mutations write an audit row inside the same SQLite transaction as the state change.
- **Idempotent CLI persistence**: Running against a file-backed database initialises the schema and only seeds sample records when the `departments` table is empty.

## Project Layout

```text
engineering-ops-db/
├── src/company_db/
│   ├── schema.sql      # 3NF DDL with foreign keys, CHECK constraints, and indexes
│   ├── manager.py      # CompanyDatabaseManager repository, CTE queries, seed data
│   └── cli.py          # Command-line runner supporting --db and --json output
├── tests/
│   └── test_manager.py # Constraint, aggregation, snapshot, and CLI tests
├── pyproject.toml
└── requirements.txt
```

## Quick Start

Run tests and linting from the repository root:

```bash
pip install -e ".[dev]"
ruff check .
pytest -v
```

Run the interactive CLI report (in-memory sample dataset, text or JSON):

```bash
PYTHONPATH=src python -m company_db.cli
PYTHONPATH=src python -m company_db.cli --db ops.db --json
```
