"""Durable database queue for bounded readiness audits, not numerical runs."""

import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from .db import engine_for, jobs, now
from .readiness import assess


def work_once(engine):
    with engine.begin() as conn:
        row = conn.execute(select(jobs).where(jobs.c.state == "QUEUED").limit(1)).mappings().first()
        if not row:
            return False
        body = {**row["body"], "started_at": now()}
        claim = conn.execute(
            jobs.update()
            .where(jobs.c.id == row["id"], jobs.c.state == "QUEUED")
            .values(state="RUNNING", body=body)
        )
        if claim.rowcount != 1:
            return True
    try:
        result = assess(body["project"], body["datasets"])
        body = {**body, "finished_at": now(), "result": result}
        state = "SUCCEEDED"  # audit execution succeeded; result remains NOT ready
    except Exception:  # noqa: BLE001 -- worker must persist failure instead of losing a claimed job
        body = {**body, "finished_at": now(), "error": "Audit failed; check input contracts"}
        state = "FAILED"
    with engine.begin() as conn:
        conn.execute(
            jobs.update()
            .where(jobs.c.id == row["id"], jobs.c.state == "RUNNING")
            .values(state=state, body=body)
        )
    return True


def recover_stale(engine):
    cutoff = datetime.now(UTC) - timedelta(minutes=5)
    with engine.begin() as conn:
        for row in conn.execute(select(jobs).where(jobs.c.state == "RUNNING")).mappings():
            if datetime.fromisoformat(row["body"]["started_at"]) < cutoff:
                conn.execute(
                    jobs.update()
                    .where(jobs.c.id == row["id"], jobs.c.state == "RUNNING")
                    .values(
                        state="FAILED",
                        body={**row["body"], "error": "Worker lease expired; submit a new audit"},
                    )
                )


if __name__ == "__main__":
    engine = engine_for()
    while True:
        recover_stale(engine)
        if not work_once(engine):
            time.sleep(1)
