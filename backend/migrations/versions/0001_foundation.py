"""Initial project, dataset, immutable scenario and audit-queue schema."""

from alembic import op
from damsafe.db import metadata

revision = "0001"
down_revision = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    metadata.create_all(
        bind, tables=[metadata.tables[n] for n in ("projects", "datasets", "scenarios", "jobs")]
    )
    if bind.dialect.name == "sqlite":
        for table in ("scenarios", "datasets"):
            op.execute(
                f"CREATE TRIGGER {table}_immutable_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable record'); END"
            )
            op.execute(
                f"CREATE TRIGGER {table}_immutable_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, 'immutable record'); END"
            )
    else:
        op.execute(
            "CREATE FUNCTION reject_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable record'; END; $$"
        )
        for table in ("scenarios", "datasets"):
            op.execute(
                f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_mutation()"
            )


def downgrade():
    raise RuntimeError("Destructive downgrade intentionally unavailable; restore a backup")
