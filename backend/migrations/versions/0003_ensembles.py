"""Immutable user-configured scenario ensembles."""

from alembic import op
from damsafe.db import ensembles

revision = "0003"
down_revision = "0002"


def upgrade():
    ensembles.create(op.get_bind(), checkfirst=True)


def downgrade():
    raise RuntimeError("Restore a backup instead of destroying ensemble evidence")
