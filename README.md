# OpsLedger

[![Python CI](https://github.com/16lv/opsledger/actions/workflows/ci.yml/badge.svg)](https://github.com/16lv/opsledger/actions/workflows/ci.yml)

**OpsLedger** is a relational database management tool written in **Python 3.12** and **SQLite 3** (`sqlite3`) for tracking a technology company's engineering departments, staff, cloud infrastructure services, and operational incidents.

## Why I Built It

In university database coursework, it is easy to write isolated `SELECT` statements without thinking about how application code manages transactions, enforces referential integrity, or avoids subtle aggregation bugs when joining multiple one-to-many tables. I built OpsLedger to practise designing a normalised 3NF schema with strict database-level constraints (`FOREIGN KEY`, `CHECK`, `UNIQUE`) and pairing every state change with an atomic audit trail.

## Relational Schema (`src/company_db/schema.sql`)

```text
departments (1) ──────< (N) employees (1) ──────< (N) cloud_services (1) ──────< (N) incidents
     │                                                      │
     └──────────────────────────< (N) ──────────────────────┘
```

- **`departments`** — Department code (`PLAT`, `DATA`, `SEC`), name, and annual budget (`CHECK (annual_budget_gbp >= 0)`).
- **`employees`** — Engineering staff linked via `FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT`, with basic email format validation and positive salary checks.
- **`cloud_services`** — Production, staging, and internal services owned by a department and lead engineer, tracking monthly cloud cost and operational status (`operational`, `degraded`, `maintenance`).
- **`incidents`** — Service incident logs (`SEV-1`, `SEV-2`, `SEV-3`), resolution state, and recovery duration in minutes.
- **`audit_log`** — Append-only operational ledger written inside the same SQLite transaction as every department creation, hire, transfer, service registration, and incident resolution.

## Key Implementation Decisions

1. **Explicit `PRAGMA foreign_keys = ON`**: SQLite disables foreign-key enforcement by default on every new connection for backwards compatibility. `CompanyDatabaseManager` enables `PRAGMA foreign_keys = ON;` immediately when opening a connection so orphan records are rejected at the storage layer.
2. **Pre-Aggregated CTEs for Budget Rollups**: Joining `departments` directly to both `employees` and `cloud_services` in a single flat `LEFT JOIN` multiplies employee salary rows whenever a department runs more than one cloud service. `get_department_budget_summary()` computes `emp_totals` and `svc_totals` in separate Common Table Expressions (`WITH` clauses) before joining them back to `departments`.
3. **Unbiased MTTR Calculation**: Open incidents have `duration_minutes = 0`. `get_service_reliability_summary()` uses `AVG(CASE WHEN i.resolved = 1 THEN i.duration_minutes END)` so unresolved incidents return `NULL` inside the aggregate and do not artificially lower a service's Mean Time To Recovery.

## Project Structure

```text
opsledger/
├── pyproject.toml
├── requirements.txt
├── src/
│   └── company_db/
│       ├── __init__.py
│       ├── cli.py          # Terminal table formatter & --json snapshot exporter
│       ├── manager.py      # CompanyDatabaseManager & transactional operations
│       └── schema.sql      # 3NF DDL schema, CHECK rules & composite indexes
└── tests/
    └── test_manager.py     # Pytest suite covering CTE rollups, constraints & CLI
```

## Getting Started

```bash
# Install development dependencies (pytest, ruff)
pip install -r requirements.txt

# Run the CLI report against an in-memory seeded database
PYTHONPATH=.:src python -m company_db.cli

# Export a structured JSON snapshot
PYTHONPATH=.:src python -m company_db.cli --json
```

### Example Terminal Output

```text
=== DEPARTMENT HEADCOUNT, PAYROLL & CLOUD BUDGET SUMMARY ===
DEPT   NAME                     STAFF      PAYROLL     CLOUD/YR     REMAINING
----------------------------------------------------------------------------
DATA   Data & Analytics             1 GBP   76,000 GBP   34,200 GBP   199,800
PLAT   Platform Engineering         2 GBP  150,000 GBP   43,200 GBP   226,800
SEC    Security Operations          1 GBP   71,000 GBP   17,400 GBP   171,600

=== CLOUD SERVICE RELIABILITY & INCIDENT SUMMARY ===
SERVICE              DEPT   STATUS        INCIDENTS   OPEN   AVG MTTR
----------------------------------------------------------------------
k8s-control-plane    PLAT   degraded              2      1    34.0 m
auth-gateway         SEC    operational           1      0     8.0 m
telemetry-ingest     DATA   operational           1      0    19.0 m
```

## Running Tests & Linter

```bash
python -m ruff check .
python -m pytest -v
```

## Known Limitations & Future Improvements

- Currency values for salaries and budgets are stored as integer GBP while monthly cloud costs use `NUMERIC`. Converting all monetary columns to integer pence would match the pattern used in `ClearLedger`.
- Schema migrations are currently initialised via `schema.sql`; adding versioned migration scripts would make evolving persistent on-disk databases cleaner.
