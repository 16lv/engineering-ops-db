"""Relational database management operations for a technology company."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Self

SCHEMA_PATH = Path(__file__).with_name("schema.sql")


@dataclass(frozen=True)
class DepartmentBudgetReport:
    """Aggregated headcount, payroll, and cloud spend per department."""

    code: str
    name: str
    active_headcount: int
    annual_payroll_gbp: int
    annual_cloud_spend_gbp: float
    annual_budget_gbp: int
    remaining_budget_gbp: float


@dataclass(frozen=True)
class ServiceReliabilityReport:
    """Incident counts and recovery metrics for a managed cloud service."""

    service_code: str
    service_name: str
    department_code: str
    owner_name: str
    status: str
    total_incidents: int
    open_incidents: int
    avg_resolution_minutes: float


class CompanyDatabaseManager:
    """Manages departments, engineers, cloud services, and incidents in SQLite."""

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.db_path = str(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON;")

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self.conn.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()

    def init_schema(self) -> None:
        """Create tables and indexes defined in schema.sql."""
        ddl = SCHEMA_PATH.read_text(encoding="utf-8")
        with self.conn:
            self.conn.executescript(ddl)
            self.conn.execute("PRAGMA foreign_keys = ON;")

    def _record_audit(
        self, action: str, entity_type: str, entity_ref: str, detail: str
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO audit_log (action, entity_type, entity_ref, detail)
            VALUES (?, ?, ?, ?)
            """,
            (action, entity_type, entity_ref, detail),
        )

    def create_department(self, code: str, name: str, annual_budget_gbp: int) -> int:
        """Insert a department and record an audit log entry."""
        clean_code = code.strip().upper()
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO departments (code, name, annual_budget_gbp)
                VALUES (?, ?, ?)
                """,
                (clean_code, name.strip(), annual_budget_gbp),
            )
            self._record_audit(
                "CREATE_DEPT",
                "department",
                clean_code,
                f"Created department '{name}' with budget GBP {annual_budget_gbp:,}",
            )
            return int(cursor.lastrowid or 0)

    def hire_employee(
        self,
        emp_code: str,
        full_name: str,
        email: str,
        role_title: str,
        department_id: int,
        salary_gbp: int,
        hired_date: str = "2026-01-15",
    ) -> int:
        """Add an employee to a department within a transaction."""
        clean_code = emp_code.strip().upper()
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO employees (
                    emp_code, full_name, email, role_title,
                    department_id, salary_gbp, is_active, hired_date
                )
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    clean_code,
                    full_name.strip(),
                    email.strip().lower(),
                    role_title.strip(),
                    department_id,
                    salary_gbp,
                    hired_date,
                ),
            )
            self._record_audit(
                "HIRE_EMPLOYEE",
                "employee",
                clean_code,
                f"Hired {full_name} ({role_title}) into department_id={department_id}",
            )
            return int(cursor.lastrowid or 0)

    def transfer_employee(
        self,
        emp_code: str,
        new_department_id: int,
        new_role_title: str | None = None,
        new_salary_gbp: int | None = None,
    ) -> None:
        """Atomically transfer an employee to a new department and log the change."""
        clean_code = emp_code.strip().upper()
        with self.conn:
            row = self.conn.execute(
                "SELECT id, role_title, salary_gbp FROM employees WHERE emp_code = ?",
                (clean_code,),
            ).fetchone()
            if row is None:
                raise ValueError(f"Employee '{clean_code}' not found.")

            updated_role = new_role_title.strip() if new_role_title else row["role_title"]
            updated_salary = new_salary_gbp if new_salary_gbp is not None else row["salary_gbp"]

            self.conn.execute(
                """
                UPDATE employees
                SET department_id = ?, role_title = ?, salary_gbp = ?
                WHERE emp_code = ?
                """,
                (new_department_id, updated_role, updated_salary, clean_code),
            )
            self._record_audit(
                "TRANSFER_EMPLOYEE",
                "employee",
                clean_code,
                f"Transferred to department_id={new_department_id} as '{updated_role}'",
            )

    def register_service(
        self,
        service_code: str,
        service_name: str,
        department_id: int,
        owner_employee_id: int,
        environment: str,
        monthly_cost_gbp: float,
        status: str = "operational",
    ) -> int:
        """Register an internal or production cloud service."""
        clean_code = service_code.strip().lower()
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO cloud_services (
                    service_code, service_name, department_id,
                    owner_employee_id, environment, monthly_cost_gbp, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean_code,
                    service_name.strip(),
                    department_id,
                    owner_employee_id,
                    environment,
                    monthly_cost_gbp,
                    status,
                ),
            )
            self._record_audit(
                "REGISTER_SERVICE",
                "cloud_service",
                clean_code,
                f"Registered {service_name} ({environment}) at GBP {monthly_cost_gbp:.2f}/mo",
            )
            return int(cursor.lastrowid or 0)

    def log_incident(
        self,
        service_id: int,
        reported_by_id: int,
        severity: str,
        summary: str,
        resolved: bool = False,
        duration_minutes: int = 0,
        logged_at: str = "2026-10-12T14:20:00Z",
    ) -> int:
        """Log a service incident and update the audit trail."""
        with self.conn:
            cursor = self.conn.execute(
                """
                INSERT INTO incidents (
                    service_id, reported_by_id, severity,
                    summary, resolved, duration_minutes, logged_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    service_id,
                    reported_by_id,
                    severity,
                    summary.strip(),
                    1 if resolved else 0,
                    duration_minutes,
                    logged_at,
                ),
            )
            incident_id = int(cursor.lastrowid or 0)
            self._record_audit(
                "LOG_INCIDENT",
                "incident",
                f"INC-{incident_id:04d}",
                f"{severity} on service_id={service_id}: {summary.strip()}",
            )
            return incident_id

    def get_department_budget_summary(self) -> list[DepartmentBudgetReport]:
        """Compute active headcount, payroll, annualized cloud cost, and remaining budget."""
        query = """
            WITH emp_totals AS (
                SELECT
                    department_id,
                    COUNT(*) AS active_headcount,
                    COALESCE(SUM(salary_gbp), 0) AS annual_payroll_gbp
                FROM employees
                WHERE is_active = 1
                GROUP BY department_id
            ),
            svc_totals AS (
                SELECT
                    department_id,
                    COALESCE(ROUND(SUM(monthly_cost_gbp) * 12.0, 2), 0.0) AS annual_cloud_spend_gbp
                FROM cloud_services
                GROUP BY department_id
            )
            SELECT
                d.code,
                d.name,
                COALESCE(e.active_headcount, 0) AS active_headcount,
                COALESCE(e.annual_payroll_gbp, 0) AS annual_payroll_gbp,
                COALESCE(s.annual_cloud_spend_gbp, 0.0) AS annual_cloud_spend_gbp,
                d.annual_budget_gbp,
                ROUND(
                    d.annual_budget_gbp
                    - COALESCE(e.annual_payroll_gbp, 0)
                    - COALESCE(s.annual_cloud_spend_gbp, 0.0),
                    2
                ) AS remaining_budget_gbp
            FROM departments d
            LEFT JOIN emp_totals e ON e.department_id = d.id
            LEFT JOIN svc_totals s ON s.department_id = d.id
            ORDER BY d.code ASC;
        """
        rows = self.conn.execute(query).fetchall()
        return [
            DepartmentBudgetReport(
                code=row["code"],
                name=row["name"],
                active_headcount=int(row["active_headcount"]),
                annual_payroll_gbp=int(row["annual_payroll_gbp"]),
                annual_cloud_spend_gbp=float(row["annual_cloud_spend_gbp"]),
                annual_budget_gbp=int(row["annual_budget_gbp"]),
                remaining_budget_gbp=float(row["remaining_budget_gbp"]),
            )
            for row in rows
        ]

    def get_service_reliability_summary(self) -> list[ServiceReliabilityReport]:
        """Join services, departments, owners, and incidents to report service reliability."""
        query = """
            SELECT
                cs.service_code,
                cs.service_name,
                d.code AS department_code,
                e.full_name AS owner_name,
                cs.status,
                COUNT(i.id) AS total_incidents,
                COALESCE(SUM(CASE WHEN i.resolved = 0 THEN 1 ELSE 0 END), 0) AS open_incidents,
                COALESCE(
                    ROUND(AVG(CASE WHEN i.resolved = 1 THEN i.duration_minutes END), 1),
                    0.0
                ) AS avg_resolution_minutes
            FROM cloud_services cs
            JOIN departments d ON d.id = cs.department_id
            JOIN employees e ON e.id = cs.owner_employee_id
            LEFT JOIN incidents i ON i.service_id = cs.id
            GROUP BY cs.id, cs.service_code, cs.service_name, d.code, e.full_name, cs.status
            ORDER BY total_incidents DESC, cs.service_code ASC;
        """
        rows = self.conn.execute(query).fetchall()
        return [
            ServiceReliabilityReport(
                service_code=row["service_code"],
                service_name=row["service_name"],
                department_code=row["department_code"],
                owner_name=row["owner_name"],
                status=row["status"],
                total_incidents=int(row["total_incidents"]),
                open_incidents=int(row["open_incidents"]),
                avg_resolution_minutes=float(row["avg_resolution_minutes"]),
            )
            for row in rows
        ]

    def search_employees(
        self,
        department_code: str | None = None,
        role_keyword: str | None = None,
        only_active: bool = True,
    ) -> list[dict[str, Any]]:
        """Run a parameterized search across employees and their assigned department."""
        clauses: list[str] = []
        params: list[Any] = []

        if only_active:
            clauses.append("e.is_active = 1")
        if department_code:
            clauses.append("d.code = ?")
            params.append(department_code.strip().upper())
        if role_keyword:
            clauses.append("LOWER(e.role_title) LIKE ?")
            params.append(f"%{role_keyword.strip().lower()}%")

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"""
            SELECT
                e.emp_code,
                e.full_name,
                e.email,
                e.role_title,
                d.code AS department_code,
                e.salary_gbp,
                e.is_active
            FROM employees e
            JOIN departments d ON d.id = e.department_id
            {where_sql}
            ORDER BY e.emp_code ASC;
        """
        return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def get_recent_audit_logs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return the most recent audit log entries."""
        rows = self.conn.execute(
            """
            SELECT id, action, entity_type, entity_ref, detail, recorded_at
            FROM audit_log
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def export_snapshot(self) -> dict[str, Any]:
        """Export a structured dictionary snapshot of budget and reliability reports."""
        return {
            "departments": [asdict(r) for r in self.get_department_budget_summary()],
            "services": [asdict(r) for r in self.get_service_reliability_summary()],
            "audit_count": len(self.get_recent_audit_logs(limit=100)),
        }


def seed_sample_company(db: CompanyDatabaseManager) -> None:
    """Populate the database with realistic sample data for a technology company."""
    db.init_schema()

    plat_id = db.create_department("PLAT", "Platform Engineering", 420_000)
    data_id = db.create_department("DATA", "Data & Analytics", 310_000)
    sec_id = db.create_department("SEC", "Security Operations", 260_000)

    e1 = db.hire_employee(
        "EMP-101",
        "Hannah Rees",
        "h.rees@vanguard-systems.co.uk",
        "Lead Platform Engineer",
        plat_id,
        82_000,
    )
    e2 = db.hire_employee(
        "EMP-102",
        "Tariq Mahmood",
        "t.mahmood@vanguard-systems.co.uk",
        "Backend Systems Engineer",
        plat_id,
        68_000,
    )
    e3 = db.hire_employee(
        "EMP-103",
        "Elena Novak",
        "e.novak@vanguard-systems.co.uk",
        "Senior Data Engineer",
        data_id,
        76_000,
    )
    e4 = db.hire_employee(
        "EMP-104",
        "Callum Price",
        "c.price@vanguard-systems.co.uk",
        "Security Engineer",
        sec_id,
        71_000,
    )

    s_auth = db.register_service(
        "auth-gateway",
        "Zero-Trust Auth Gateway",
        sec_id,
        e4,
        "production",
        1_450.0,
        "operational",
    )
    s_ingest = db.register_service(
        "telemetry-ingest",
        "Kafka Telemetry Ingestion",
        data_id,
        e3,
        "production",
        2_850.0,
        "operational",
    )
    s_kube = db.register_service(
        "k8s-control-plane",
        "Cluster Control Plane",
        plat_id,
        e1,
        "production",
        3_600.0,
        "degraded",
    )

    db.log_incident(
        s_kube,
        e2,
        "SEV-2",
        "Node pool autoscaler latency spike in eu-west-2",
        resolved=True,
        duration_minutes=34,
    )
    db.log_incident(
        s_kube,
        e1,
        "SEV-3",
        "CoreDNS cache eviction warning during deployment rollout",
        resolved=False,
        duration_minutes=0,
    )
    db.log_incident(
        s_ingest,
        e3,
        "SEV-2",
        "Consumer lag threshold exceeded on partition 4",
        resolved=True,
        duration_minutes=19,
    )
    db.log_incident(
        s_auth,
        e4,
        "SEV-3",
        "Upstream OIDC key rotation retry",
        resolved=True,
        duration_minutes=8,
    )
