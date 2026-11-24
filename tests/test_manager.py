"""Automated test suite for CompanyDatabaseManager."""

from __future__ import annotations

import json
import sqlite3

import pytest

from company_db.cli import format_report_text, main
from company_db.manager import CompanyDatabaseManager, seed_sample_company


def test_department_budget_and_cloud_spend_aggregation() -> None:
    with CompanyDatabaseManager(":memory:") as db:
        seed_sample_company(db)
        reports = {r.code: r for r in db.get_department_budget_summary()}

        assert set(reports.keys()) == {"DATA", "PLAT", "SEC"}

        plat = reports["PLAT"]
        assert plat.active_headcount == 2
        assert plat.annual_payroll_gbp == 150_000
        assert plat.annual_cloud_spend_gbp == 43_200.0
        assert plat.remaining_budget_gbp == 226_800.0

        data = reports["DATA"]
        assert data.active_headcount == 1
        assert data.annual_payroll_gbp == 76_000
        assert data.annual_cloud_spend_gbp == 34_200.0
        assert data.remaining_budget_gbp == 199_800.0


def test_service_reliability_and_incident_resolution() -> None:
    with CompanyDatabaseManager(":memory:") as db:
        seed_sample_company(db)
        services = {s.service_code: s for s in db.get_service_reliability_summary()}

        kube = services["k8s-control-plane"]
        assert kube.total_incidents == 2
        assert kube.open_incidents == 1
        assert kube.avg_resolution_minutes == 34.0

        # Resolve the open CoreDNS incident (id=2) with a 26-minute recovery time
        db.resolve_incident(incident_id=2, duration_minutes=26)

        updated_kube = {
            s.service_code: s for s in db.get_service_reliability_summary()
        }["k8s-control-plane"]
        assert updated_kube.open_incidents == 0
        # Average of 34m and 26m is 30.0m
        assert updated_kube.avg_resolution_minutes == 30.0

        with pytest.raises(ValueError, match="already resolved"):
            db.resolve_incident(incident_id=2, duration_minutes=10)


def test_employee_transfer_updates_department_and_audit_log() -> None:
    with CompanyDatabaseManager(":memory:") as db:
        seed_sample_company(db)
        sec_dept_row = db.conn.execute(
            "SELECT id FROM departments WHERE code = 'SEC'"
        ).fetchone()
        assert sec_dept_row is not None

        db.transfer_employee(
            "EMP-102",
            new_department_id=int(sec_dept_row["id"]),
            new_role_title="Principal Security Systems Engineer",
            new_salary_gbp=78_000,
        )

        sec_staff = db.search_employees(department_code="SEC")
        codes = [emp["emp_code"] for emp in sec_staff]
        assert "EMP-102" in codes

        audits = db.get_recent_audit_logs(limit=5)
        assert audits[0]["action"] == "TRANSFER_EMPLOYEE"
        assert audits[0]["entity_ref"] == "EMP-102"


def test_foreign_key_and_check_constraints_enforced() -> None:
    with CompanyDatabaseManager(":memory:") as db:
        db.init_schema()
        dept_id = db.create_department("CORE", "Core Engineering", 200_000)

        # Invalid salary (<= 0) should trigger SQLite CHECK constraint failure
        with pytest.raises(sqlite3.IntegrityError):
            db.hire_employee(
                "EMP-900",
                "Invalid Salary User",
                "invalid@vanguard-systems.co.uk",
                "Engineer",
                dept_id,
                salary_gbp=0,
            )

        # Non-existent department_id should trigger FOREIGN KEY constraint failure
        with pytest.raises(sqlite3.IntegrityError):
            db.hire_employee(
                "EMP-901",
                "Orphan Department User",
                "orphan@vanguard-systems.co.uk",
                "Engineer",
                department_id=9999,
                salary_gbp=55_000,
            )


def test_cli_text_and_json_modes(capsys: pytest.CaptureFixture[str]) -> None:
    with CompanyDatabaseManager(":memory:") as db:
        seed_sample_company(db)
        text = format_report_text(db)
        assert "k8s-control-plane" in text
        assert "Platform Engineering" in text

    exit_code = main(["--json"])
    assert exit_code == 0
    captured = capsys.readouterr().out
    payload = json.loads(captured)
    assert len(payload["departments"]) == 3
    assert len(payload["services"]) == 3


def test_export_snapshot_counts_more_than_100_audit_entries_and_rejects_blank_inputs(
    tmp_path: pytest.TempPathFactory,
) -> None:
    db_file = tmp_path / "persistent.db"
    assert main(["--db", str(db_file), "--json"]) == 0
    # Running CLI a second time against an existing database should not duplicate or fail
    assert main(["--db", str(db_file), "--json"]) == 0

    with CompanyDatabaseManager(":memory:") as db:
        db.init_schema()
        with pytest.raises(ValueError, match="Department code"):
            db.create_department("   ", "Platform", 100_000)

        dept_id = db.create_department("OPS", "Operations", 300_000)
        for idx in range(115):
            db.hire_employee(
                f"EMP-{idx:03d}",
                f"Engineer {idx}",
                f"eng{idx}@example.co.uk",
                "Developer",
                dept_id,
                50_000,
            )

        snapshot = db.export_snapshot()
        assert snapshot["audit_count"] == 116


def test_validation_guards_and_employee_deactivation() -> None:
    with CompanyDatabaseManager(":memory:") as db:
        seed_sample_company(db)

        dept_id = int(db.conn.execute("SELECT id FROM departments WHERE code = 'PLAT'").fetchone()["id"])

        with pytest.raises(ValueError, match="valid YYYY-MM-DD"):
            db.hire_employee("EMP-500", "Bad Date", "b@example.co.uk", "Dev", dept_id, 50_000, hired_date="15/01/2026")

        with pytest.raises(ValueError, match="New role title"):
            db.transfer_employee("EMP-102", new_department_id=dept_id, new_role_title="   ")

        with pytest.raises(ValueError, match="Unresolved incidents"):
            db.log_incident(1, 1, "SEV-2", "Still open", resolved=False, duration_minutes=20)

        # Deactivating EMP-101 removes GBP 82,000 from PLAT active payroll
        db.deactivate_employee("EMP-101")
        plat_after = {r.code: r for r in db.get_department_budget_summary()}["PLAT"]
        assert plat_after.active_headcount == 1
        assert plat_after.annual_payroll_gbp == 68_000

        with pytest.raises(ValueError, match="already inactive"):
            db.deactivate_employee("EMP-101")


def test_cli_department_filter_and_audit_log_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--json", "--dept", "PLAT", "--audit-limit", "3"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [d["code"] for d in payload["departments"]] == ["PLAT"]
    assert len(payload["recent_audit_logs"]) == 3


def test_cli_role_filter_and_negative_audit_limit_exit_code(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["--json", "--role", "Platform"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [e["emp_code"] for e in payload["matching_employees"]] == ["EMP-101"]

    assert main(["--audit-limit", "-1"]) == 2
    assert "error:" in capsys.readouterr().err
