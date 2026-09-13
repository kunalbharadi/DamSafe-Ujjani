import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    create_engine,
    event,
)

metadata = MetaData()
projects = Table(
    "projects", metadata, Column("id", String, primary_key=True), Column("body", JSON, nullable=False)
)
datasets = Table(
    "datasets",
    metadata,
    Column("id", String, primary_key=True),
    Column("project_id", ForeignKey("projects.id"), nullable=False),
    Column("name", String, nullable=False),
    Column("version", Integer, nullable=False),
    Column("body", JSON, nullable=False),
)
scenarios = Table(
    "scenarios",
    metadata,
    Column("id", String, primary_key=True),
    Column("project_id", ForeignKey("projects.id"), nullable=False),
    Column("body", JSON, nullable=False),
)
jobs = Table(
    "jobs",
    metadata,
    Column("id", String, primary_key=True),
    Column("project_id", ForeignKey("projects.id"), nullable=False),
    Column("state", String, nullable=False),
    Column("body", JSON, nullable=False),
)

runs = Table(
    "runs",
    metadata,
    Column("id", String, primary_key=True),
    Column("project_id", ForeignKey("projects.id"), nullable=False),
    Column("idempotency_key", String, nullable=False),
    Column("state", String, nullable=False),
    Column("input", JSON, nullable=False),
    Column("result", JSON, nullable=False),
    UniqueConstraint("project_id", "idempotency_key", name="uq_run_submission"),
)


def now():
    return datetime.now(UTC).isoformat()


def uid():
    return str(uuid4())


def engine_for(url=None):
    url = url or os.environ.get("DAMSAFE_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Set DAMSAFE_DATABASE_URL; use scripts/start.ps1 -Preview for explicit SQLite preview"
        )
    if url.startswith("sqlite"):
        Path(".local").mkdir(exist_ok=True)
    engine = create_engine(url, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def pragmas(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=10000")

    return engine
