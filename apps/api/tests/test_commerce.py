import asyncio
import hashlib
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select, text, update

from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import (
    CartItem,
    CartRow,
    DataSource,
    ImportBatch,
    Inventory,
    MockPayment,
    Order,
    OrderItem,
    ProductAttribute,
    ProductImage,
    ProductRow,
    ProductSource,
    ProductVariant,
    SearchQuery,
    SellerOffer,
    SellerProfile,
    SessionRow,
    Shipment,
    SourceProduct,
    StockReservation,
    User,
    UserRole,
)
from app.main import app

ORIGIN = {"Origin": "http://localhost:3000"}


async def member():
    c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=ORIGIN)
    token = (await c.get("/api/v1/auth/csrf")).json()["token"]
    c.headers["X-CSRF-Token"] = token
    response = await c.post(
        "/api/v1/auth/register",
        json={
            "email": f"commerce-{uuid.uuid4().hex}@example.invalid",
            "password": "temporary-test-password-123",
        },
    )
    assert response.status_code == 201, response.text
    c.headers["X-CSRF-Token"] = c.cookies["hm_csrf"]
    return c, response.json()["id"]


@pytest.fixture(autouse=True)
async def cleanup():
    async with session_factory() as s:
        snapshot = [
            (r.offer_id, r.on_hand, r.reserved, r.version)
            for r in (await s.scalars(select(Inventory))).all()
        ]
    yield
    async with session_factory.begin() as s:
        ids = list(
            (
                await s.scalars(
                    select(User.id).where(User.email.like("commerce-%@example.invalid"))
                )
            ).all()
        )
        await s.execute(
            update(Order).where(Order.id == "fixture-order").values(user_id="fixture-customer")
        )
        orders = list((await s.scalars(select(Order.id).where(Order.user_id.in_(ids)))).all())
        for model in [StockReservation, MockPayment, Shipment, OrderItem]:
            await s.execute(delete(model).where(model.order_id.in_(orders)))
        await s.execute(delete(Order).where(Order.id.in_(orders)))
        await s.execute(delete(SearchQuery).where(SearchQuery.user_id.in_(ids)))
        for model in [CartItem, CartRow, SessionRow, UserRole, SellerProfile]:
            await s.execute(delete(model).where(model.user_id.in_(ids)))
        products = list(
            (
                await s.scalars(
                    select(ProductRow.id)
                    .join(SellerOffer, SellerOffer.product_id == ProductRow.id)
                    .where(SellerOffer.seller_id.in_(ids))
                )
            ).all()
        )
        offers = select(SellerOffer.id).where(SellerOffer.product_id.in_(products))
        await s.execute(delete(Inventory).where(Inventory.offer_id.in_(offers)))
        await s.execute(delete(SellerOffer).where(SellerOffer.product_id.in_(products)))
        for model in [ProductSource, ProductAttribute, ProductImage, ProductVariant]:
            await s.execute(delete(model).where(model.product_id.in_(products)))
        await s.execute(delete(ProductRow).where(ProductRow.id.in_(products)))
        sources = ["operator-" + i for i in ids]
        await s.execute(delete(SourceProduct).where(SourceProduct.source_id.in_(sources)))
        await s.execute(delete(ImportBatch).where(ImportBatch.source_id.in_(sources)))
        await s.execute(delete(DataSource).where(DataSource.id.in_(sources)))
        await s.execute(delete(User).where(User.id.in_(ids)))
        for offer, on_hand, reserved, version in snapshot:
            await s.execute(
                update(Inventory)
                .where(Inventory.offer_id == offer)
                .values(on_hand=on_hand, reserved=reserved, version=version)
            )
    await engine.dispose()


async def payload(c):
    product = (await c.get("/api/v1/products/sweater-01")).json()
    return {
        "items": [
            {"product_id": product["id"], "quantity": 1, "expected_price_vnd": product["price_vnd"]}
        ],
        "method": "mock",
        "address": {
            "recipient": "Khách mô phỏng",
            "phone": "0900000000",
            "address_line": "Địa chỉ kiểm thử mô phỏng",
        },
    }


async def test_auth_csrf_hash_logout_and_roles():
    c, uid = await member()
    try:
        assert "HttpOnly" in str(c.cookies) or (await c.get("/api/v1/auth/me")).status_code == 200
        async with session_factory() as s:
            user = await s.get(User, uid)
            assert user.password_hash.startswith("$argon2id$")
            token = (
                await s.scalars(select(SessionRow.token_hash).where(SessionRow.user_id == uid))
            ).one()
            assert token == hashlib.sha256(c.cookies["hm_session"].encode()).hexdigest()
        assert (await c.get("/api/v1/manage/products")).status_code == 403
        assert (
            await c.patch(
                "/api/v1/history",
                json={"enabled": True},
                headers={"Origin": "https://evil.invalid"},
            )
        ).status_code == 403
        assert (
            await c.patch(
                "/api/v1/history", json={"enabled": True}, headers={"X-CSRF-Token": "bad"}
            )
        ).status_code == 403
        assert (await c.post("/api/v1/auth/logout")).status_code == 200
        assert (await c.get("/api/v1/auth/me")).status_code == 401
        c.headers["X-CSRF-Token"] = (await c.get("/api/v1/auth/csrf")).json()["token"]
        bad = await c.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "incorrect-password-123"}
        )
        missing = await c.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.invalid", "password": "incorrect-password-123"},
        )
        assert bad.status_code == missing.status_code == 401 and bad.json() == missing.json()
        valid = await c.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "temporary-test-password-123"},
        )
        assert valid.status_code == 200
        assert "HttpOnly" in valid.headers["set-cookie"]
    finally:
        await c.aclose()


async def test_tc5_owner_and_tc6_read_only():
    c, uid = await member()
    other, _ = await member()
    try:
        async with session_factory.begin() as s:
            await s.execute(update(Order).where(Order.id == "fixture-order").values(user_id=uid))

        async def snapshot():
            async with session_factory() as s:
                return [
                    (
                        table,
                        (
                            await s.execute(
                                text(f"SELECT row_to_json(t)::text FROM {table} t ORDER BY 1")
                            )
                        )
                        .scalars()
                        .all(),
                    )
                    for table in [
                        "products",
                        "seller_offers",
                        "inventory",
                        "orders",
                        "order_items",
                        "stock_reservations",
                        "mock_payments",
                        "shipments",
                    ]
                ]

        before = await snapshot()
        result = await c.get("/api/v1/search/text", params={"q": "kiểm tra đơn hàng 20261005"})
        assert result.status_code == 200, result.text
        assert result.json()["search_type"] == "order"
        order = result.json()["order"]
        assert order["status"] == "CONFIRMED" and order["total_vnd"] == 710500
        assert sorted(x["unit_price_vnd"] for x in order["items"]) == [115500, 595000]
        assert before == await snapshot()
        own_missing = await other.get("/api/v1/orders/20261005")
        unknown = await other.get("/api/v1/orders/does-not-exist")
        assert own_missing.status_code == unknown.status_code == 404
        assert own_missing.json() == unknown.json()
        assert (
            await other.get("/api/v1/search/text", params={"q": "đơn hàng 20261005"})
        ).status_code == 404
        assert (
            await other.patch("/api/v1/orders/20261005", json={"status": "CANCELLED"})
        ).status_code == 404
    finally:
        await c.aclose()
        await other.aclose()


async def test_cart_price_stale_idempotency_and_cancel():
    c, _ = await member()
    try:
        body = await payload(c)
        assert (
            await c.put(
                "/api/v1/cart", json={"items": [{"product_id": "sweater-01", "quantity": 1}]}
            )
        ).status_code == 200
        stale = json.loads(json.dumps(body))
        stale["items"][0]["expected_price_vnd"] -= 1
        assert (
            await c.post(
                "/api/v1/checkout", json=stale, headers={"Idempotency-Key": uuid.uuid4().hex}
            )
        ).status_code == 409
        key = uuid.uuid4().hex
        first, second = await asyncio.gather(
            *[
                c.post("/api/v1/checkout", json=body, headers={"Idempotency-Key": key})
                for _ in range(2)
            ]
        )
        assert first.status_code == second.status_code == 201, (first.text, second.text)
        assert first.json()["code"] == second.json()["code"]
        assert (await c.get("/api/v1/cart")).json()["items"] == []
        body["method"] = "cod"
        assert (
            await c.post("/api/v1/checkout", json=body, headers={"Idempotency-Key": key})
        ).status_code == 409
        code = first.json()["code"]
        for _ in range(2):
            assert (
                await c.patch(f"/api/v1/orders/{code}", json={"status": "CANCELLED"})
            ).status_code == 200
        async with session_factory() as s:
            stock = await s.get(Inventory, "offer-sweater-01")
            assert stock.reserved == 0
    finally:
        await c.aclose()


async def test_two_buyers_cannot_oversell():
    c, _ = await member()
    other, _ = await member()
    try:
        body = await payload(c)
        async with session_factory.begin() as s:
            await s.execute(
                update(Inventory)
                .where(Inventory.offer_id == "offer-sweater-01")
                .values(on_hand=1, reserved=0)
            )
        responses = await asyncio.gather(
            *[
                buyer.post(
                    "/api/v1/checkout", json=body, headers={"Idempotency-Key": uuid.uuid4().hex}
                )
                for buyer in [c, other]
            ]
        )
        assert sorted(r.status_code for r in responses) == [201, 409], [r.text for r in responses]
        async with session_factory() as s:
            stock = await s.get(Inventory, "offer-sweater-01")
            assert stock.on_hand == stock.reserved == 1
    finally:
        await c.aclose()
        await other.aclose()


async def test_history_opt_in_ownership_delete():
    c, _ = await member()
    other, _ = await member()
    try:
        await c.get("/api/v1/search/text", params={"q": "áo len"})
        assert (await c.get("/api/v1/history")).json() == []
        assert (await c.patch("/api/v1/history", json={"enabled": True})).status_code == 200
        await c.get("/api/v1/search/text", params={"q": "áo len"})
        assert len((await c.get("/api/v1/history")).json()) == 1
        assert (await other.get("/api/v1/history")).json() == []
        await c.patch("/api/v1/history", json={"enabled": False})
        assert (await c.get("/api/v1/history")).json() == []
    finally:
        await c.aclose()
        await other.aclose()


async def test_admin_draft_review_price_and_fulfillment():
    c, uid = await member()
    try:
        async with session_factory.begin() as s:
            s.add(UserRole(user_id=uid, role="admin"))
        async with session_factory() as s:
            image = (await s.scalars(select(ProductImage.id).limit(1))).one()
        draft = {
            "name": "Áo kiểm thử nguyên bản",
            "description": "Dữ liệu mô phỏng do người vận hành tạo",
            "category_id": "ao-len-nam",
            "image_id": image,
            "price_vnd": 100000,
            "stock": 5,
            "color": "đen",
            "material": "len",
            "size": "M",
            "original_data_confirmed": True,
        }
        preview = await c.post("/api/v1/manage/imports/preview", json={"records": [draft]})
        assert preview.status_code == 200 and preview.json()["errors"] == []
        invalid = {**draft, "category_id": "missing-category"}
        assert (await c.post("/api/v1/manage/imports/preview", json={"records": [invalid]})).json()[
            "errors"
        ]
        assert (
            await c.post("/api/v1/manage/imports", json={"records": [invalid]})
        ).status_code == 422
        imported = await c.post("/api/v1/manage/imports", json={"records": [draft]})
        assert imported.status_code == 201, imported.text
        repeated = await c.post("/api/v1/manage/imports", json={"records": [draft]})
        assert imported.json()["created"][0]["id"] == repeated.json()["created"][0]["id"]
        assert (
            await c.get("/api/v1/products/" + imported.json()["created"][0]["id"])
        ).status_code == 404
        response = await c.post("/api/v1/manage/products", json=draft)
        assert response.status_code == 201, response.text
        pid = response.json()["id"]
        assert (await c.get(f"/api/v1/products/{pid}")).status_code == 404
        assert (await c.post(f"/api/v1/manage/products/{pid}/publish")).status_code == 200
        assert (await c.get(f"/api/v1/products/{pid}")).status_code == 200
        body = await payload(c)
        created = await c.post(
            "/api/v1/checkout", json=body, headers={"Idempotency-Key": uuid.uuid4().hex}
        )
        code = created.json()["code"]
        assert (
            await c.patch(f"/api/v1/orders/{code}", json={"status": "DELIVERED"})
        ).status_code == 409
        for status in ["PACKING", "SHIPPED", "DELIVERED"]:
            assert (
                await c.patch(f"/api/v1/orders/{code}", json={"status": status})
            ).status_code == 200
        assert (
            await c.patch(f"/api/v1/orders/{code}", json={"status": "CANCELLED"})
        ).status_code == 409
        assert (await c.post(f"/api/v1/manage/products/{pid}/archive")).status_code == 200
    finally:
        await c.aclose()


async def test_chunked_request_bound_before_parser(client):
    async def chunks():
        for _ in range(140):
            yield b"x" * 1024

    response = await client.post(
        "/api/v1/search/text", content=chunks(), headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 413


async def test_seller_only_owns_drafts_and_cannot_publish():
    seller, uid = await member()
    other, other_uid = await member()
    try:
        async with session_factory.begin() as s:
            s.add(UserRole(user_id=uid, role="seller"))
            s.add(SellerProfile(user_id=uid, name="Bán hàng mô phỏng", approved=True))
            s.add(UserRole(user_id=other_uid, role="seller"))
            s.add(SellerProfile(user_id=other_uid, name="Người bán khác", approved=True))
        async with session_factory() as s:
            image = (await s.scalars(select(ProductImage.id).limit(1))).one()
        draft = {
            "name": "Áo người bán mô phỏng",
            "description": "Mô tả nguyên bản mô phỏng có quyền sử dụng",
            "category_id": "ao-len-nam",
            "image_id": image,
            "price_vnd": 90000,
            "stock": 3,
            "color": "đen",
            "material": "len",
            "size": "M",
            "original_data_confirmed": True,
        }
        created = await seller.post("/api/v1/manage/products", json=draft)
        assert created.status_code == 201, created.text
        pid = created.json()["id"]
        assert (await seller.post(f"/api/v1/manage/products/{pid}/publish")).status_code == 403
        assert (
            await other.patch(
                f"/api/v1/manage/products/{pid}", json={"price_vnd": 100000, "stock": 3}
            )
        ).status_code == 404
        assert (await other.get("/api/v1/manage/products")).json()["items"] == []
        assert (
            await seller.post("/api/v1/manage/imports/preview", json={"records": [draft]})
        ).status_code == 403
    finally:
        await seller.aclose()
        await other.aclose()


async def test_history_bound_retention_and_expired_session():
    from datetime import UTC, datetime, timedelta

    from app.core.dependencies import commerce_service

    c, uid = await member()
    try:
        await c.patch("/api/v1/history", json={"enabled": True})
        async with session_factory.begin() as s:
            for i in range(105):
                s.add(
                    SearchQuery(
                        id=uuid.uuid4().hex,
                        user_id=uid,
                        raw_text="Câu tìm kiếm mô phỏng",
                        modality="text",
                        created_at=datetime.now(UTC) - timedelta(seconds=i),
                    )
                )
            s.add(
                SearchQuery(
                    id="expired-history",
                    user_id=uid,
                    raw_text="Đã hết hạn",
                    modality="text",
                    created_at=datetime.now(UTC) - timedelta(days=8),
                )
            )
        await c.get("/api/v1/search/text", params={"q": "áo len"})
        assert len((await c.get("/api/v1/history")).json()) == 100
        service = commerce_service()
        actor = await service.identify(c.cookies["hm_session"])
        await asyncio.gather(
            service.store.remember(actor, "áo len", "text", ["sweater-01"]),
            service.store.history(actor, "disable"),
        )
        assert (await c.get("/api/v1/history")).json() == []
        await commerce_service().store.maintenance()
        async with session_factory.begin() as s:
            assert await s.get(SearchQuery, "expired-history") is None
            await s.execute(
                update(SessionRow)
                .where(SessionRow.user_id == uid)
                .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
            )
        assert (await c.get("/api/v1/auth/me")).status_code == 401
    finally:
        await c.aclose()
