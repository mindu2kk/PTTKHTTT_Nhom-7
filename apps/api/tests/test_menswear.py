import pytest
from sqlalchemy import func, select, update

from app.domain.catalog import CatalogFilter
from app.domain.commerce import Actor, BusinessError
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.commerce import SqlCommerceStore
from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import CategoryRow, ProductRow


async def test_menswear_visibility_preserves_legacy_products_and_filters():
    async with session_factory() as session:
        try:
            before = await session.scalar(select(func.count()).select_from(ProductRow))
            await session.execute(update(CategoryRow).values(is_active=CategoryRow.id.like("nam%")))
            repository = SqlCatalogRepository(session, "demo_seed")
            categories = await repository.categories()
            assert [sum(c.level == level for c in categories) for level in range(3)] == [1, 3, 19]
            assert len(await SqlCatalogRepository(session, "real_demo").categories()) == 23
            assert (await repository.list_products(CatalogFilter()))[1] == 0
            assert await repository.get_product("sweater-01") is None
            assert await session.scalar(select(func.count()).select_from(ProductRow)) == before
            # Original demo data, changed only inside this rolled-back test transaction.
            await session.execute(
                update(ProductRow)
                .where(ProductRow.id == "sweater-01")
                .values(category_id="nam-ao-ni-len")
            )
            for category in ("nam", "nam-ao", "nam-ao-ni-len"):
                items, total = await repository.list_products(CatalogFilter(category=category))
                assert total == 1 and items[0].id == "sweater-01"
            assert (await repository.list_products(CatalogFilter(category="nam-quan")))[1] == 0
            assert (await repository.list_products(CatalogFilter(category="ao-len-nam")))[1] == 0
        finally:
            await session.rollback()
    await engine.dispose()


async def test_inactive_category_rejected_before_product_creation():
    async with session_factory() as session:
        try:
            await session.execute(
                update(CategoryRow).where(CategoryRow.id == "ao-len-nam").values(is_active=False)
            )
            store = SqlCommerceStore(session_factory, "demo_seed")
            actor = Actor("fixture-customer", "fixture-customer@example.invalid", ("admin",), False)
            with pytest.raises(BusinessError) as error:
                await store._create(
                    session,
                    actor,
                    {
                        "category_id": "ao-len-nam",
                        "original_data_confirmed": True,
                    },
                )
            assert error.value.status == 422
        finally:
            await session.rollback()
    await engine.dispose()
