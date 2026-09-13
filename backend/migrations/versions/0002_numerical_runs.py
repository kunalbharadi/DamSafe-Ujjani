"""Durable numerical runs with immutable submission manifests."""

from alembic import op
from damsafe.db import runs

revision = "0002"
down_revision = "0001"


def upgrade():
    bind = op.get_bind()
    runs.create(bind, checkfirst=True)
    if bind.dialect.name == "sqlite":
        op.execute(
            "CREATE TRIGGER runs_input_immutable BEFORE UPDATE OF input, project_id, idempotency_key ON runs BEGIN SELECT RAISE(ABORT, 'immutable run input'); END"
        )
    else:
        op.execute(
            "CREATE TRIGGER runs_input_immutable BEFORE UPDATE OF input, project_id, idempotency_key ON runs FOR EACH ROW EXECUTE FUNCTION reject_mutation()"
        )


def downgrade():
    raise RuntimeError("Restore a backup instead of destroying run evidence")
