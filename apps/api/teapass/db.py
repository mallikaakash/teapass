from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from teapass.config import Settings


def make_database(settings: Settings):
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        hide_parameters=True,
        connect_args={"connect_timeout": 5, "options": "-c statement_timeout=10000"},
    )
    return engine, sessionmaker(engine, expire_on_commit=False)
