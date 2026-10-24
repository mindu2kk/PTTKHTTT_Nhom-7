"""Create only the explicitly named *_test DB. Never print the connection secret."""

import os

import psycopg
from dotenv import dotenv_values
from psycopg import sql
from sqlalchemy.engine import make_url


def test_url() -> str:
    value = os.environ.get("TEST_DATABASE_URL") or dotenv_values(".env").get(
        "TEST_DATABASE_URL"
    )
    if not value:
        raise RuntimeError("Set TEST_DATABASE_URL in .env")
    parsed = make_url(value)
    if not parsed.database or not parsed.database.endswith("_test"):
        raise RuntimeError("Refusing: test DB name must end in _test")
    if parsed.drivername != "postgresql+psycopg":
        raise RuntimeError("Use postgresql+psycopg")
    return value


if __name__ == "__main__":
    url = make_url(test_url())
    conninfo = url.set(drivername="postgresql", database="postgres").render_as_string(
        hide_password=False
    )
    with psycopg.connect(conninfo, autocommit=True) as conn:
        if not conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (url.database,)
        ).fetchone():
            conn.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(url.database or ""))
            )
    print("Separate test database ready (credentials hidden).")
