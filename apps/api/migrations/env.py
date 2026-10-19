from alembic import context
from sqlalchemy import create_engine

import teapass.workflow_models  # noqa: F401
from teapass.config import Settings
from teapass.models import Base

engine = create_engine(Settings().database_url, hide_parameters=True)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
