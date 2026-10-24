import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings


def configure_event_loop() -> None:
    # psycopg async needs SelectorEventLoop on Windows (not default Proactor).
    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


configure_event_loop()
engine = create_async_engine(
    get_settings().database_url.get_secret_value(),
    pool_size=5,
    max_overflow=5,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 3, "options": "-c statement_timeout=3000"},
)
session_factory = async_sessionmaker(engine, expire_on_commit=False)
