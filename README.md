# Company Database Manager (`company-db-manager`)

[![Python CI](https://github.com/16lv/company-db-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/16lv/company-db-manager/actions/workflows/ci.yml)

A relational database management tool written in **Python 3.12** and **SQLite 3** (`sqlite3`) for managing a technology company's engineering departments, employees, cloud services, and operational incidents.

Built to demonstrate practical relational schema design (3NF), foreign-key and `CHECK` constraints, transactional updates with audit logging, and multi-table SQL reporting queries (`WITH` CTEs, `LEFT JOIN`, `GROUP BY`, and conditional aggregations).

---

## Relational Schema (`src/company_db/schema.sql`)

- **`departments`** — Department code, name, and annual budget (`CHECK (annual_budget_gbp >= 0)`).
- **`employees`** — Engineering staff linked via `FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT`, with email validation and salary constraints.
- **`cloud_services`** — Production and internal services owned by a department and lead engineer, tracking monthly infrastructure cost and operational status (`operational`, `degraded`, `maintenance`).
- **`incidents`** — Service incident records (`SEV-1`, `SEV-2`, `SEV-3`), resolution status, and recovery duration in minutes.
- **`audit_log`** — Append-only operational ledger recording every department creation, hire, transfer, service registration, and incident report.

---

## Quick Start

```bash
# Install development dependencies
pip install -r requirements.txt

# Run the CLI report against an in-memory seeded database
PYTHONPATH=.:src python -m company_db.cli

# Export structured JSON snapshot
PYTHONPATH=.:src python -m company_db.cli --json

# Run linter and automated test suite
python -m ruff check .
python -m pytest -v
```

### Example Output

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
