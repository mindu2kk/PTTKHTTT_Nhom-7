import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from dotenv import dotenv_values
from httpx import ASGITransport, AsyncClient
from sqlalchemy import update
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[3]
value = os.environ.get("TEST_DATABASE_URL") or dotenv_values(ROOT / ".env").get("TEST_DATABASE_URL")
if not value or not (make_url(value).database or "").endswith("_test"):
    raise RuntimeError("Tests require a separate TEST_DATABASE_URL database ending in _test")
os.environ["DATABASE_URL"] = value
os.environ["DATA_PROFILE"] = "demo_seed"
os.environ["LOCAL_ONLY"] = "true"

from app.infrastructure.database import engine, session_factory  # noqa: E402
from app.infrastructure.models import CategoryRow  # noqa: E402
from app.infrastructure.seed import seed  # noqa: E402
from app.main import app  # noqa: E402


def migrate(target: str) -> None:
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            str(ROOT / "apps/api/alembic.ini"),
            "downgrade" if target == "base" else "upgrade",
            target,
        ],
        check=True,
        cwd=ROOT,
    )


async def initialize() -> None:
    async with session_factory.begin() as session:
        await seed(session)
        # Legacy fixture regression; menswear tests explicitly switch the active tree.
        ids = [
            c["id"]
            for c in json.loads(
                (ROOT / "benchmarks/fixtures/catalog.json").read_text(encoding="utf-8")
            )["categories"]
        ]
        await session.execute(update(CategoryRow).values(is_active=CategoryRow.id.in_(ids)))
    await engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def database():
    # Only the explicitly guarded test database is rebuilt. Never touch the developer DB.
    migrate("base")
    migrate("head")
    asyncio.run(initialize())
    yield
    asyncio.run(engine.dispose())
    migrate("base")
    migrate("head")
    asyncio.run(initialize())


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    await engine.dispose()
