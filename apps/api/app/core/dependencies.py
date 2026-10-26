from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import text

from app.application.catalog import ProductService
from app.application.commerce import CommerceService
from app.application.image_search import ImageSearchService
from app.application.search import SearchOrchestrator
from app.application.shopping_assistant import ShoppingAssistant
from app.application.speech import SpeechService
from app.core.config import get_settings
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.commerce import SqlCommerceStore
from app.infrastructure.database import session_factory
from app.infrastructure.media import (
    HttpImageEncoder,
    HttpSpeechRecognizer,
    HttpTextEncoder,
    PillowMediaValidator,
)
from app.infrastructure.passwords import ArgonPasswords
from app.infrastructure.vectors import SqlImageVectorIndex

FIXTURE_ROOT = Path(__file__).resolve().parents[4] / "benchmarks" / "fixtures"
CATALOG_MEDIA_ROOT = Path(__file__).resolve().parents[4] / "data" / "catalog" / "images"
CATALOG_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
image_encoder = HttpImageEncoder(get_settings().inference_url)
text_encoder = HttpTextEncoder(get_settings().inference_url)
passwords = ArgonPasswords()


def commerce_service() -> CommerceService:
    return CommerceService(
        SqlCommerceStore(session_factory, get_settings().data_profile), passwords
    )


async def maintenance_loop() -> None:
    import asyncio

    while True:
        try:
            await commerce_service().store.maintenance()
        except Exception:
            pass
        await asyncio.sleep(3600)


async def product_service() -> AsyncIterator[ProductService]:
    async with session_factory() as session:
        yield ProductService(SqlCatalogRepository(session, get_settings().data_profile))


async def database_ready() -> bool:
    async with session_factory() as session:
        # Readiness must prove the expected schema revision, not only an open TCP port.
        revision = await session.scalar(text("SELECT version_num FROM alembic_version"))
        return bool(revision == "0009_product_image_order")


async def search_service() -> AsyncIterator[SearchOrchestrator]:
    async with session_factory() as session:
        yield SearchOrchestrator(SqlCatalogRepository(session, get_settings().data_profile))


async def image_service() -> AsyncIterator[ImageSearchService]:
    async with session_factory() as session:
        yield ImageSearchService(
            SearchOrchestrator(SqlCatalogRepository(session, get_settings().data_profile)),
            PillowMediaValidator(),
            image_encoder,
            SqlImageVectorIndex(session),
        )


async def speech_service() -> AsyncIterator[SpeechService]:
    async with session_factory() as session:
        yield SpeechService(
            HttpSpeechRecognizer(get_settings().inference_url),
            SqlCatalogRepository(session, get_settings().data_profile),
        )


async def shopping_assistant() -> AsyncIterator[ShoppingAssistant]:
    async with session_factory() as session:
        yield ShoppingAssistant(
            SearchOrchestrator(SqlCatalogRepository(session, get_settings().data_profile)),
            text_encoder,
            SqlImageVectorIndex(session),
        )
