# engineering-ops-db

Relational database manager and command-line reporting utility built with **Python 3.12** and **SQLite 3**. Models departments, staff payroll, cloud service bills, incidents, and transactional audit logs using a third-normal-form (3NF) schema.

## Design Highlights

- **Accurate multi-table summaries**: Joining `departments` directly to both `employees` and `cloud_services` causes row multiplication whenever a team runs multiple services. `get_department_budget_summary()` sums payroll (`emp_totals`) and annualised cloud costs (`svc_totals`) in separate Common Table Expressions before joining back to `departments`.
- **Database & domain checks**: Enables `PRAGMA foreign_keys = ON`, validates dates (`YYYY-MM-DD`), emails, non-blank fields, and positive budgets/salaries, and prevents unresolved incidents from carrying a recovery duration.
- **Transactional audit trail**: Staff hires, transfers, deactivations, service registrations, and incident updates write to `audit_log` inside the same transaction as the state change.
- **Reliable resolution averages**: `get_service_reliability_summary()` calculates `AVG(CASE WHEN i.resolved = 1 THEN i.duration_minutes END)` so open incidents (`0` minutes) never deflate MTTR.

## Project Structure

```text
engineering-ops-db/
├── src/company_db/
│   ├── schema.sql      # 3NF schema with foreign keys, CHECK constraints, and indexes
│   ├── manager.py      # CompanyDatabaseManager, CTE queries, validation, sample seeder
│   └── cli.py          # Terminal table and JSON reporter (--db, --json)
├── tests/
│   └── test_manager.py
├── pyproject.toml
└── requirements.txt
```

## Quick Start

```bash
pip install -e ".[dev]"
ruff check .
pytest -v
```

Run the CLI report against an in-memory sample dataset or a persistent SQLite file:

```bash
PYTHONPATH=src python -m company_db.cli
PYTHONPATH=src python -m company_db.cli --db ops.db --json
```
