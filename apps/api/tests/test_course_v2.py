from app.application.search import SearchOrchestrator
from app.domain.search import SearchOptions
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.course_fixture import apply_course_v2
from app.infrastructure.database import engine, session_factory


async def test_slide_price_revision_preserves_v1_and_repeats():
    async with session_factory() as s:
        transaction = await s.begin()
        try:
            assert (await apply_course_v2(s))["updated"] == 2
            await s.flush()
            assert (await apply_course_v2(s))["already_applied"] == 2
            result = await SearchOrchestrator(SqlCatalogRepository(s, "demo_seed")).search(
                "túi đeo chéo màu đỏ dưới 150k", options=SearchOptions(allow_relax=("color",))
            )
            assert result.total == 3
            assert sorted(r.product.price_vnd for r in result.items) == [95000, 99000, 149000]
            assert result.items[0].product.id == "bag-red"
        finally:
            await transaction.rollback()
    await engine.dispose()
