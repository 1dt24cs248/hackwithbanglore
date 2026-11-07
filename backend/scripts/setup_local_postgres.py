"""Complete the local PostgreSQL setup without echoing the role password."""

from __future__ import annotations

import getpass
import json
import os
import re
import subprocess
import sys
import uuid
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.database import create_database_engine, create_session_factory
from app.models import Incident, InvestigationRun


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"
REQUIRED_TABLES = {
    "incidents",
    "investigation_runs",
    "investigation_findings",
    "incident_logs",
    "deployments",
    "engineer_feedback",
    "verified_resolutions",
    "postmortems",
    "memory_operation_events",
}


def write_status(path: Path, **values: object) -> None:
    path.write_text(json.dumps(values, sort_keys=True), encoding="utf-8")


def update_database_url(database_url: str) -> None:
    if not ENV_FILE.is_file():
        raise FileNotFoundError("backend/.env was not found")
    content = ENV_FILE.read_text(encoding="utf-8")
    lines = content.splitlines()
    indexes = [
        index
        for index, line in enumerate(lines)
        if re.match(r"^\s*(?:export\s+)?DATABASE_URL\s*=", line)
    ]
    if len(indexes) > 1:
        raise RuntimeError("backend/.env has multiple DATABASE_URL assignments")
    assignment = f"DATABASE_URL={database_url}"
    if indexes:
        lines[indexes[0]] = assignment
    else:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(assignment)
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_role_and_create_database(password: str) -> tuple[str, bool]:
    catalog_url = URL.create(
        "postgresql+psycopg",
        username="postgres",
        password=password,
        host="127.0.0.1",
        port=5432,
        database="postgres",
    )
    engine = create_engine(catalog_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            role = connection.execute(
                text(
                    "SELECT rolname, rolcanlogin, rolcreatedb, rolsuper "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            ).one_or_none()
        if role is None or role.rolname != "postgres" or not role.rolcanlogin:
            raise RuntimeError("The postgres role is unavailable or cannot log in")
        if not role.rolcreatedb and not role.rolsuper:
            raise RuntimeError("The postgres role cannot create a database")

        database_engine = create_engine(catalog_url, pool_pre_ping=True)
        try:
            with database_engine.connect().execution_options(
                isolation_level="AUTOCOMMIT"
            ) as connection:
                exists = connection.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :name"),
                    {"name": "incidentiq"},
                ).scalar_one_or_none()
                if exists is None:
                    connection.execute(text("CREATE DATABASE incidentiq"))
                    created = True
                else:
                    created = False
        finally:
            database_engine.dispose()
        return role.rolname, created
    finally:
        engine.dispose()


def run_postgres_crud(database_url: str) -> None:
    engine = create_database_engine(database_url)
    factory = create_session_factory(engine)
    incident_number = f"INC-PG-VERIFY-{uuid.uuid4().hex[:12]}"
    incident_id = None
    try:
        with factory() as session:
            incident = Incident(
                incident_number=incident_number,
                title="Temporary PostgreSQL CRUD verification",
                description="Synthetic test row created and removed by the verification script.",
                service_name="incidentiq-test",
                environment="test",
                severity="low",
                status="open",
                source="api",
                synthetic_data=True,
                is_demo=True,
            )
            session.add(incident)
            session.commit()
            incident_id = incident.id

        with factory() as session:
            incident = session.get(Incident, incident_id)
            if incident is None or incident.incident_number != incident_number:
                raise RuntimeError("PostgreSQL CRUD read did not return the created incident")
            incident.title = "Temporary PostgreSQL CRUD verification updated"
            session.commit()

        with factory() as session:
            incident = session.scalar(
                select(Incident).where(Incident.incident_number == incident_number)
            )
            if incident is None or not incident.title.endswith("updated"):
                raise RuntimeError("PostgreSQL CRUD update was not persisted")
            run = InvestigationRun(
                incident_id=incident.id,
                memory_mode="off",
                execution_status="succeeded",
            )
            session.add(run)
            session.flush()
            if run.incident_id != incident.id:
                raise RuntimeError("PostgreSQL relationship read did not match the incident")
            session.delete(run)
            session.flush()
            session.delete(incident)
            session.commit()
    finally:
        if incident_id is not None:
            with factory() as session:
                incident = session.get(Incident, incident_id)
                if incident is not None:
                    for run in list(incident.investigation_runs):
                        session.delete(run)
                    session.delete(incident)
                    session.commit()
        engine.dispose()


def main(status_path: Path) -> int:
    stage = "password_prompt"
    password = getpass.getpass(
        "Enter the existing PostgreSQL password for role postgres (input hidden): "
    )
    if not password:
        write_status(status_path, result="failed", stage=stage, error="empty_password")
        print("No password entered; setup stopped without changing the database.", flush=True)
        return 1

    try:
        stage = "verify_role_and_database"
        role_name, created = verify_role_and_create_database(password)
        print(f"Verified PostgreSQL login role: {role_name}", flush=True)
        print(
            "Database incidentiq " + ("created." if created else "already exists."),
            flush=True,
        )

        database_url = URL.create(
            "postgresql+psycopg",
            username="postgres",
            password=password,
            host="127.0.0.1",
            port=5432,
            database="incidentiq",
        ).render_as_string(hide_password=False)
        update_database_url(database_url)
        os.environ["DATABASE_URL"] = database_url
        print("Configured DATABASE_URL in backend/.env (value hidden).", flush=True)

        stage = "sqlalchemy_connection"
        engine = create_database_engine(database_url)
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1")).scalar_one()
                version = connection.execute(text("SELECT version()")).scalar_one()
                database_name = connection.execute(
                    text("SELECT current_database()")
                ).scalar_one()
            version_match = re.search(r"PostgreSQL\s+(\d+)", version)
            version_major = version_match.group(1) if version_match else "unknown"
            if database_name != "incidentiq" or version_major != "18":
                raise RuntimeError("Connected to an unexpected database or PostgreSQL version")
        finally:
            engine.dispose()
        print("SQLAlchemy connection verified: PostgreSQL 18, database incidentiq.", flush=True)

        stage = "migration_preflight"
        engine = create_database_engine(database_url)
        try:
            table_names = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()
        if table_names - {"alembic_version"} and "alembic_version" not in table_names:
            raise RuntimeError("Unversioned tables exist; migration stopped to protect data")

        stage = "alembic_upgrade"
        config = Config(str(BACKEND_DIR / "alembic.ini"))
        command.upgrade(config, "head")
        engine = create_database_engine(database_url)
        try:
            table_names = set(inspect(engine).get_table_names())
        finally:
            engine.dispose()
        missing_tables = REQUIRED_TABLES - table_names
        if missing_tables:
            raise RuntimeError("Migration completed without all expected tables")
        print("Alembic migration applied; all nine expected tables are present.", flush=True)

        stage = "postgresql_crud"
        run_postgres_crud(database_url)
        print("PostgreSQL CRUD create/read/update/delete verification passed.", flush=True)

        stage = "backend_test_suite"
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=BACKEND_DIR,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )
        output = completed.stdout + completed.stderr
        summary = re.search(r"Ran\s+(\d+)\s+tests?.*?(?:OK|FAILED.*)", output, re.S)
        test_summary = summary.group(0).strip() if summary else "Test output summary unavailable"
        print(test_summary, flush=True)
        if completed.returncode != 0:
            raise RuntimeError("The backend test suite reported failures")

        write_status(
            status_path,
            result="success",
            role=role_name,
            database="incidentiq",
            postgres_major=version_major,
            migration="head",
            tables=sorted(REQUIRED_TABLES),
            crud="passed",
            tests=test_summary,
        )
        print("PostgreSQL setup and verification completed.", flush=True)
        password = ""
        return 0
    except Exception as error:
        write_status(
            status_path,
            result="failed",
            stage=stage,
            error_category=type(error).__name__,
        )
        print(
            f"Setup stopped during {stage}; safe error category: {type(error).__name__}. "
            "No exception details or credentials were printed.",
            flush=True,
        )
        password = ""
        return 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Internal setup status path was not supplied.")
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1])))
