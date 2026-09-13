"""Idempotent project bootstrap from external site configuration."""

from pathlib import Path

from damsafe.contracts import ProjectInput
from damsafe.db import engine_for, projects, uid
from sqlalchemy import insert, select

root = Path(__file__).resolve().parents[1]
site = ProjectInput.model_validate_json((root / "config/ujjani.json").read_text(encoding="utf-8"))
with engine_for().begin() as conn:
    existing = [r.body for r in conn.execute(select(projects))]
    if not any(p["site_key"] == site.site_key for p in existing):
        conn.execute(insert(projects).values(id=uid(), body=site.model_dump(mode="json")))
        print("Created Ujjani project; study bounds remain unverified")
    else:
        print("Ujjani project already exists; preserved it")
