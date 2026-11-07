"""Secure, interactive setup and verification for local IncidentIQ PostgreSQL.

The password is entered through getpass and is never printed or written to this
script's status report. Run from the backend directory or pass an optional
status-file path as the first argument.
"""
from __future__ import annotations

import getpass
import json
import os
import sys
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import URL


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
ENV_FILE = BACKEND / ".env"
EXPECTED_TABLES = {
    "incidents", "investigation_runs", "investigation_findings",
    "incident_logs", "deployments", "engineer_feedback",
    "verified_resolutions", "postmortems", "memory_operation_events",
}


def status_file() -> Path | None:
    return Path(sys.argv[1]) if len(sys.argv) > 1 else None


def report(state: dict) -> None:
    path = status_file()
    if path:
        path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def set_database_url(value: str) -> None:
    original = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    lines = original.splitlines()
    matches = [i for i, line in enumerate(lines) if line.strip().startswith("DATABASE_URL=")]
    if len(matches) > 1:
        raise RuntimeError("multiple DATABASE_URL entries")
    assignment = "DATABASE_URL=" + value
    if matches:
        lines[matches[0]] = assignment
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(assignment)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    state: dict = {"status": "started"}
    report(state)
    password = getpass.getpass("PostgreSQL password for role postgres (input hidden): ")
    if not password:
        raise RuntimeError("empty password")

    catalog_url = URL.create("postgresql+psycopg", username="postgres", password=password,
                             host="127.0.0.1", port=5432, database="postgres")
    catalog = create_engine(catalog_url, pool_pre_ping=True)
    try:
        needs_create = False
        with catalog.connect() as conn:
            role = conn.execute(text("""SELECT rolname, rolcanlogin, rolsuper, rolcreatedb
                                      FROM pg_roles WHERE rolname = current_user""")).one()
            if role.rolname != "postgres" or not role.rolcanlogin:
                raise RuntimeError("unexpected database role")
            state["role_verified"] = True
            state["role_can_create_database"] = bool(role.rolsuper or role.rolcreatedb)
            exists = conn.execute(text("SELECT 1 FROM pg_database WHERE datname = 'incidentiq'")).scalar()
            if not exists:
                if not (role.rolsuper or role.rolcreatedb):
                    raise RuntimeError("role cannot create database")
                needs_create = True
        if needs_create:
            with catalog.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
                conn.execute(text('CREATE DATABASE "incidentiq"'))
        state["database_created"] = needs_create
        state["database_exists"] = True
        report(state)
    finally:
        catalog.dispose()

    db_url = URL.create("postgresql+psycopg", username="postgres", password=password,
                        host="127.0.0.1", port=5432, database="incidentiq")
    set_database_url(db_url.render_as_string(hide_password=False))
    os.environ["DATABASE_URL"] = db_url.render_as_string(hide_password=False)
    del password

    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            facts = conn.execute(text("SELECT current_database(), current_user, version()" )).one()
            if facts[0] != "incidentiq" or facts[1] != "postgres":
                raise RuntimeError("unexpected connection target")
            if "PostgreSQL 18" not in facts[2]:
                raise RuntimeError("server is not PostgreSQL 18")
            state["sqlalchemy_connection"] = True
            state["server_major"] = 18
        report(state)

        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        app_tables = existing - {"alembic_version"}
        if app_tables and "alembic_version" not in existing:
            raise RuntimeError("unversioned tables exist; migration stopped to protect data")
        cfg = Config(str(BACKEND / "alembic.ini"))
        command.upgrade(cfg, "head")
        tables = set(inspect(engine).get_table_names())
        missing = EXPECTED_TABLES - tables
        if missing:
            raise RuntimeError("expected tables missing after migration")
        state["migration"] = "succeeded"
        state["tables_verified"] = sorted(EXPECTED_TABLES)
        report(state)

        # Use one uniquely named test incident and its child; clean up only these
        # rows in a transaction, never truncate or touch existing records.
        suffix = uuid.uuid4().hex[:12]
        incident_id = uuid.uuid4()
        run_id = uuid.uuid4()
        with engine.begin() as conn:
            conn.execute(text("""INSERT INTO incidents
                               (id, incident_number, title, description, service_name,
                                environment, severity, status, source)
                               VALUES (:id, :number, :title, :description, :service,
                                       :environment, :severity, :status, :source)"""),
                         {"id": incident_id, "number": "SETUP-" + suffix.upper(),
                          "title": "PostgreSQL setup verification",
                          "description": "Temporary CRUD verification record",
                          "service": "setup-check", "environment": "local",
                          "severity": "low", "status": "open", "source": "test"})
            conn.execute(text("""INSERT INTO investigation_runs
                               (id, incident_id, memory_mode, execution_status)
                               VALUES (:id, :incident_id, :memory_mode, :status)"""),
                         {"id": run_id, "incident_id": incident_id,
                          "memory_mode": "off", "status": "queued"})
            selected = conn.execute(text("SELECT title FROM incidents WHERE id=:id"),
                                    {"id": incident_id}).scalar_one()
            if selected != "PostgreSQL setup verification":
                raise RuntimeError("CRUD read failed")
            conn.execute(text("UPDATE incidents SET status='resolved' WHERE id=:id"),
                         {"id": incident_id})
            updated = conn.execute(text("SELECT status FROM incidents WHERE id=:id"),
                                   {"id": incident_id}).scalar_one()
            if updated != "resolved":
                raise RuntimeError("CRUD update failed")
            conn.execute(text("DELETE FROM investigation_runs WHERE id=:id"), {"id": run_id})
            conn.execute(text("DELETE FROM incidents WHERE id=:id"), {"id": incident_id})
        state["crud"] = "succeeded (insert/read/update/delete; temporary rows removed)"
        state["status"] = "succeeded"
        report(state)
        print("PostgreSQL setup, migration, table verification, and CRUD succeeded.")
        return 0
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        safe_state = {"status": "failed", "error_category": type(exc).__name__}
        report(safe_state)
        print("Setup did not complete. Safe error category:", type(exc).__name__)
        sys.exit(1)
