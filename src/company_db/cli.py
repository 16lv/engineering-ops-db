"""CLI entry point for inspecting tech company database reports."""

from __future__ import annotations

import argparse
import json
from typing import Sequence

from company_db.manager import CompanyDatabaseManager, seed_sample_company


def format_report_text(db: CompanyDatabaseManager) -> str:
    """Format department financial and service reliability reports for terminal output."""
    lines: list[str] = []
    lines.append("=== DEPARTMENT HEADCOUNT, PAYROLL & CLOUD BUDGET SUMMARY ===")
    lines.append(
        f"{'DEPT':<6} {'NAME':<24} {'STAFF':>5} {'PAYROLL':>12} {'CLOUD/YR':>12} {'REMAINING':>13}"
    )
    lines.append("-" * 76)

    for dept in db.get_department_budget_summary():
        lines.append(
            f"{dept.code:<6} {dept.name:<24} {dept.active_headcount:>5} "
            f"GBP {dept.annual_payroll_gbp:>8,} "
            f"GBP {dept.annual_cloud_spend_gbp:>8,.0f} "
            f"GBP {dept.remaining_budget_gbp:>9,.0f}"
        )

    lines.append("")
    lines.append("=== CLOUD SERVICE RELIABILITY & INCIDENT SUMMARY ===")
    lines.append(
        f"{'SERVICE':<20} {'DEPT':<6} {'STATUS':<13} {'INCIDENTS':>9} {'OPEN':>6} {'AVG MTTR':>10}"
    )
    lines.append("-" * 70)

    for svc in db.get_service_reliability_summary():
        lines.append(
            f"{svc.service_code:<20} {svc.department_code:<6} {svc.status:<13} "
            f"{svc.total_incidents:>9} {svc.open_incidents:>6} "
            f"{svc.avg_resolution_minutes:>7.1f} m"
        )

    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tech company relational database manager (Python 3.12 + SQLite)"
    )
    parser.add_argument(
        "--db",
        default=":memory:",
        help="Path to SQLite database file (default: :memory:)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report instead of formatted tables",
    )
    args = parser.parse_args(argv)

    with CompanyDatabaseManager(args.db) as db:
        seed_sample_company(db)
        if args.json:
            print(json.dumps(db.export_snapshot(), indent=2))
        else:
            print(format_report_text(db))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
