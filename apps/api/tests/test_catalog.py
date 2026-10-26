import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text, update
from sqlalchemy.exc import IntegrityError

from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import (
    Base,
    DataSource,
    Inventory,
    Order,
    OrderItem,
    ProductRow,
    SellerOffer,
    User,
)
from app.infrastructure.seed import seed


async def test_health_schema_extensions(client: AsyncClient):
    assert (await client.get("/health/live")).json()["status"] == "ok"
    assert (await client.get("/health/ready")).status_code == 200
    async with session_factory() as session:
        extensions = set(await session.scalars(text("SELECT extname FROM pg_extension")))
        assert {"vector", "pg_trgm", "unaccent"}.issubset(extensions)


async def test_category_hierarchy(client: AsyncClient):
    response = await client.get("/api/v1/categories")
    assert response.status_code == 200
    cats = response.json()
    assert [sum(c["level"] == level for c in cats) for level in range(3)] == [4, 11, 34]
    by_id = {c["id"]: c for c in cats}
    for c in cats:
        if c["parent_id"] is not None:
            assert by_id[c["parent_id"]]["level"] == c["level"] - 1


async def test_only_published_safe_catalog(client: AsyncClient):
    response = await client.get("/api/v1/products", params={"page_size": 24})
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 50
    assert len(page["items"]) == 24
    for item in page["items"]:
        assert not item["id"].startswith("hidden-")
        assert item["data_notice"] == "dữ liệu mô phỏng"
        assert item["verification_status"] == "verified"
        assert item["rights_status"] == "demo"
        assert item["price_kind"] == "demo"
        assert type(item["price_vnd"]) is int
        image = await client.get(item["image_url"])
        assert image.status_code == 200
        assert "image/svg+xml" in image.headers["content-type"]


@pytest.mark.parametrize(
    "identifier",
    [
        "unknown",
        "hidden-draft",
        "hidden-unverified",
        "hidden-rights",
        "hidden-image",
        "hidden-history",
    ],
)
async def test_hidden_and_missing_detail_same_404(client: AsyncClient, identifier: str):
    response = await client.get(f"/api/v1/products/{identifier}")
    assert response.status_code == 404
    assert response.json() == {"detail": "Không tìm thấy sản phẩm."}


async def test_detail_by_id_and_slug(client: AsyncClient):
    item = (await client.get("/api/v1/products/sweater-01")).json()
    by_slug = await client.get(f"/api/v1/products/{item['slug']}")
    assert by_slug.json() == item
    assert item["price_vnd"] == 264000
    assert item["material"] == "len"


async def test_subtree_and_combined_filters(client: AsyncClient):
    page = (
        await client.get(
            "/api/v1/products",
            params={
                "category": "thoi-trang-nam",
                "color": "đen",
                "price_max": 499999,
                "gender": "nam",
                "page_size": 24,
                "sort": "price_asc",
            },
        )
    ).json()
    assert page["total"] == 10
    assert [p["price_vnd"] for p in page["items"][:3]] == [264000, 324000, 456000]
    assert all(p["category_id"] == "ao-len-nam" for p in page["items"])
    assert all(p["color"] == "đen" and p["price_vnd"] < 500000 for p in page["items"])
    assert page["items"][-1]["available_quantity"] == 0  # visible, not reserved by reads
    empty = await client.get("/api/v1/products", params={"category": "missing"})
    assert empty.json()["total"] == 0


async def test_pagination_stable_no_duplicates(client: AsyncClient):
    pages = [
        (
            await client.get(
                "/api/v1/products",
                params={
                    "page": page,
                    "page_size": 24,
                    "sort": "price_asc",
                },
            )
        ).json()["items"]
        for page in [1, 2, 3]
    ]
    items = sum(pages, [])
    assert len(items) == len({p["id"] for p in items}) == 50
    assert [p["price_vnd"] for p in items] == sorted(p["price_vnd"] for p in items)
    again = (
        await client.get(
            "/api/v1/products",
            params={
                "page_size": 24,
                "sort": "price_asc",
            },
        )
    ).json()["items"]
    assert again == pages[0]


@pytest.mark.parametrize(
    "query",
    [
        {"page_size": 25},
        {"page": 0},
        {"page_size": -1},
        {"sort": "sql"},
        {"price_min": -1},
        {"price_min": 500, "price_max": 100},
        {"price_max": "1.5"},
        {"unknown": "field"},
        {"category": "x" * 101},
    ],
)
async def test_bad_query_vietnamese_error(client: AsyncClient, query: dict):
    response = await client.get("/api/v1/products", params=query)
    assert response.status_code == 422
    assert response.json()["detail"].startswith("Thông tin không hợp lệ")


@pytest.mark.parametrize("value", ["' OR 1=1 --", "<script>alert(1)</script>", "../../.env"])
async def test_untrusted_filter_is_data(client: AsyncClient, value: str):
    response = await client.get("/api/v1/products", params={"category": value})
    assert response.status_code == 200
    assert response.json()["items"] == []


async def snapshot(session):
    return {
        table.name: (
            await session.execute(select(table).order_by(*table.primary_key.columns))
        ).all()
        for table in Base.metadata.sorted_tables
    }


async def test_seed_idempotent_and_catalog_reads_do_not_mutate(client: AsyncClient):
    async with session_factory.begin() as session:
        before = await snapshot(session)
        await seed(session)
        await seed(session)
        assert await snapshot(session) == before
    await client.get("/api/v1/products", params={"category": "ao-len-nam"})
    await client.get("/api/v1/products/sweater-01")
    await client.get("/api/v1/categories")
    async with session_factory() as session:
        assert await snapshot(session) == before


async def test_order_fixture_private_and_exact(client: AsyncClient):
    async with session_factory() as session:
        order = await session.scalar(select(Order).where(Order.code == "20261005"))
        assert order is not None and order.status == "CONFIRMED" and order.total_vnd == 710500
        total = await session.scalar(
            select(func.sum(OrderItem.unit_price_vnd * OrderItem.quantity)).where(
                OrderItem.order_id == order.id
            )
        )
        assert total == order.total_vnd
        user = await session.get(User, order.user_id)
        assert user is not None and not user.is_active and user.password_hash is None
    # Legacy POST lookup is never a public bypass; M6 rejects unsafe requests before routing.
    assert (
        await client.post("/api/v1/orders/lookup", json={"code": "20261005"})
    ).status_code == 403


@pytest.mark.parametrize(
    "statement",
    [
        update(Inventory).where(Inventory.offer_id == "offer-sweater-01").values(reserved=999),
        update(Inventory).where(Inventory.offer_id == "offer-sweater-01").values(on_hand=-1),
        update(SellerOffer).where(SellerOffer.id == "offer-sweater-01").values(price_vnd=-1),
        update(ProductRow).where(ProductRow.id == "sweater-01").values(category_id="orphan"),
        update(SellerOffer)
        .where(SellerOffer.id == "offer-sweater-01")
        .values(variant_id="variant-sweater-02"),
    ],
)
async def test_database_constraints(statement, client: AsyncClient):
    async with session_factory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(statement)
        await session.rollback()


async def test_revoking_source_immediately_hides_catalog(client: AsyncClient):
    # Roll back after querying repository on the same transaction; no durable mutation.
    from app.infrastructure.catalog import SqlCatalogRepository

    async with session_factory() as session:
        await session.execute(
            update(DataSource)
            .where(DataSource.id == "hoodoomart-original-fixture")
            .values(rights_status="restricted")
        )
        assert await SqlCatalogRepository(session, "demo_seed").get_product("sweater-01") is None
        await session.rollback()


async def test_request_id_and_headers(client: AsyncClient):
    response = await client.get("/health/live", headers={"X-Request-ID": "test_123"})
    assert response.headers["X-Request-ID"] == "test_123"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"
    unsafe = await client.get("/health/live", headers={"X-Request-ID": "<script>"})
    assert "<" not in unsafe.headers["X-Request-ID"]


async def test_approved_public_profile_excludes_demo(client: AsyncClient):
    from app.domain.catalog import CatalogFilter
    from app.infrastructure.catalog import SqlCatalogRepository

    async with session_factory() as session:
        items, total = await SqlCatalogRepository(session, "approved_public").list_products(
            CatalogFilter()
        )
        assert items == [] and total == 0


async def test_arbitrary_category_depth(client: AsyncClient):
    from app.domain.catalog import CatalogFilter
    from app.infrastructure.catalog import SqlCatalogRepository
    from app.infrastructure.models import CategoryRow

    async with session_factory() as session:
        session.add(
            CategoryRow(
                id="deep-leaf",
                slug="deep-leaf",
                name_vi="Nhánh sâu",
                parent_id="ao-len-nam",
                is_active=True,
                level=3,
                sort_order=99,
            )
        )
        await session.flush()
        await session.execute(
            update(ProductRow).where(ProductRow.id == "sweater-01").values(category_id="deep-leaf")
        )
        items, _ = await SqlCatalogRepository(session, "demo_seed").list_products(
            CatalogFilter(category="ao-nam", page_size=24)
        )
        assert "sweater-01" in {p.id for p in items}
        await session.rollback()


async def test_unavailable_database_safe_error(client: AsyncClient, monkeypatch):
    from sqlalchemy.exc import OperationalError

    import app.main as main

    async def unavailable():
        raise OperationalError("private SQL", {}, Exception("private connection"))

    monkeypatch.setattr(main, "database_ready", unavailable)
    response = await client.get("/health/ready")
    assert response.status_code == 503
    assert "private" not in response.text
    await engine.dispose()


async def test_overlapping_category_subtrees_do_not_duplicate(client: AsyncClient):
    from app.domain.catalog import CatalogFilter
    from app.infrastructure.catalog import SqlCatalogRepository

    async with session_factory() as session:
        repo = SqlCatalogRepository(session, "demo_seed")
        expected, total = await repo.list_products(CatalogFilter(category="ao-nam", page_size=100))
        actual, actual_total = await repo.list_products(
            CatalogFilter(categories=("ao-nam", "ao-len-nam"), page_size=100)
        )
        assert actual_total == total
        assert [p.id for p in actual] == [p.id for p in expected]
