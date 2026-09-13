from alembic import context
from damsafe.db import engine_for, metadata

with engine_for().connect() as connection:
    context.configure(connection=connection, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()
