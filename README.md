# engineering-ops-db

Relational database toolkit built with **Python 3.12** and **SQLite** for tracking engineering departments, employees, cloud services, operational incidents, and an append-only audit trail.

## Overview

`engineering-ops-db` models typical operations data in a normalised SQLite schema (`departments`, `employees`, `cloud_services`, `incidents`, `audit_log`) with strict `CHECK` and `FOREIGN KEY` constraints enforced at connection time.

## Features

- **Fan-out-safe financial rollups**: `get_department_budget_summary()` aggregates employee salaries and annualised cloud service costs inside separate CTEs before joining, preventing row-multiplication double counting.
- **Honest reliability averages**: `get_service_reliability_summary()` computes mean time to resolution only across resolved incidents (`resolved = 1`).
- **Validated writes & lifecycle controls**: Includes `transfer_employee()`, `deactivate_employee()`, `resolve_incident()`, ISO date checks (`YYYY-MM-DD`), and audit logging on every state transition.
- **CLI & JSON export**: Run terminal tables or JSON snapshots via `engineering-ops-db`, with `--dept` filtering and configurable `--audit-limit` history output.

## Technology Stack

- Python 3.11+ (tested on Python 3.12)
- SQLite3 (`sqlite3` standard library)
- pytest, Ruff

## Installation

```bash
pip install -e ".[dev]"
```

## Usage Examples

Print formatted budget and reliability tables:

```bash
engineering-ops-db
```

Write to a persistent database file and inspect filtered JSON output:

```bash
engineering-ops-db --db company_ops.db --dept ENG --role Platform --audit-limit 10 --json
```

## Technical Implementation Details

- SQLite disables foreign-key verification per connection by default; `CompanyDatabaseManager.__init__()` enables `PRAGMA foreign_keys = ON` on creation and again after schema setup.
- All multi-table writes (`hire_employee`, `transfer_employee`, `deactivate_employee`, `log_incident`, `resolve_incident`) wrap both the record update and its audit entry inside a single transaction.

## Project Structure

```text
engineering-ops-db/
├── src/company_db/
│   ├── __init__.py
│   ├── cli.py
│   ├── manager.py
│   └── schema.sql
├── tests/
│   └── test_manager.py
├── pyproject.toml
└── requirements.txt
```

## Testing

```bash
ruff check .
pytest -v
```

## Known Limitations & Future Improvements

- Built as a synchronous single-writer SQLite library with no migration engine; moving past schema v1 cleanly would benefit from versioned SQL migrations.
- Employee transfers and service costs operate in GBP only without multi-currency conversion.
