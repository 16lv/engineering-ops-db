-- Normalized 3NF schema for tech company operations:
-- Departments, Engineering Staff, Cloud Services, and Incident Logs.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE CHECK (length(trim(code)) >= 2),
    name TEXT NOT NULL UNIQUE,
    annual_budget_gbp INTEGER NOT NULL CHECK (annual_budget_gbp >= 0)
);

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    emp_code TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE CHECK (email LIKE '%_@__%.__%'),
    role_title TEXT NOT NULL,
    department_id INTEGER NOT NULL,
    salary_gbp INTEGER NOT NULL CHECK (salary_gbp > 0),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    hired_date TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS cloud_services (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_code TEXT NOT NULL UNIQUE,
    service_name TEXT NOT NULL,
    department_id INTEGER NOT NULL,
    owner_employee_id INTEGER NOT NULL,
    environment TEXT NOT NULL CHECK (environment IN ('production', 'staging', 'internal')),
    monthly_cost_gbp NUMERIC NOT NULL CHECK (monthly_cost_gbp >= 0),
    status TEXT NOT NULL DEFAULT 'operational'
        CHECK (status IN ('operational', 'degraded', 'maintenance')),
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE RESTRICT,
    FOREIGN KEY (owner_employee_id) REFERENCES employees(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    service_id INTEGER NOT NULL,
    reported_by_id INTEGER NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('SEV-1', 'SEV-2', 'SEV-3')),
    summary TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0 CHECK (resolved IN (0, 1)),
    duration_minutes INTEGER NOT NULL DEFAULT 0 CHECK (duration_minutes >= 0),
    logged_at TEXT NOT NULL,
    FOREIGN KEY (service_id) REFERENCES cloud_services(id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by_id) REFERENCES employees(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_ref TEXT NOT NULL,
    detail TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_employees_dept_active
    ON employees(department_id, is_active);

CREATE INDEX IF NOT EXISTS idx_services_dept_status
    ON cloud_services(department_id, status);

CREATE INDEX IF NOT EXISTS idx_incidents_service_sev
    ON incidents(service_id, severity);
