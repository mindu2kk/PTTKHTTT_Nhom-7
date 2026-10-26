import asyncio
import uuid

from sqlalchemy import select

from app.infrastructure.database import session_factory
from app.infrastructure.models import Inventory, ProductSize, UserRole

from .test_commerce import cleanup, member, payload  # noqa: F401


async def test_two_sizes_cart_checkout_ownership_and_cancel():
    client, owner_id = await member()
    other, _ = await member()
    try:
        async with session_factory.begin() as session:
            stock = await session.get(Inventory, "offer-sweater-01")
            original = await session.scalar(
                select(ProductSize).where(ProductSize.product_id == "sweater-01")
            )
            original.stock_quantity = stock.on_hand - 2
            second = ProductSize(product_id="sweater-01", size="XL", stock_quantity=2, reserved=0)
            session.add(second)
            await session.flush()
            first_id, second_id = original.id, second.id
        product = (await client.get("/api/v1/products/sweater-01")).json()
        assert len(product["sizes"]) == 2
        missing = await client.put(
            "/api/v1/cart", json={"items": [{"product_id": "sweater-01", "quantity": 1}]}
        )
        assert missing.status_code == 409
        items = [
            {"product_id": "sweater-01", "product_size_id": sid, "quantity": 1}
            for sid in (first_id, second_id)
        ]
        assert (await client.put("/api/v1/cart", json={"items": items})).status_code == 200
        assert len((await client.get("/api/v1/cart")).json()["items"]) == 2
        body = await payload(client)
        body["items"] = [{**line, "expected_price_vnd": product["price_vnd"]} for line in items]
        key = uuid.uuid4().hex
        result = await client.post("/api/v1/checkout", json=body, headers={"Idempotency-Key": key})
        assert result.status_code == 201, result.text
        order = result.json()
        assert {i["product_size_id"] for i in order["items"]} == {first_id, second_id}
        assert all(i["size"] for i in order["items"])
        assert (
            await client.post("/api/v1/checkout", json=body, headers={"Idempotency-Key": key})
        ).json() == order
        assert (
            await other.patch(f"/api/v1/orders/{order['code']}", json={"status": "CANCELLED"})
        ).status_code == 404
        assert (
            await client.patch(f"/api/v1/orders/{order['code']}", json={"status": "CANCELLED"})
        ).status_code == 200
        async with session_factory() as session:
            assert (await session.get(ProductSize, second_id)).reserved == 0
            assert (await session.get(ProductSize, second_id)).stock_quantity == 2
        async with session_factory.begin() as session:
            session.add(UserRole(user_id=owner_id, role="admin"))
        shipped = await client.post(
            "/api/v1/checkout", json=body, headers={"Idempotency-Key": uuid.uuid4().hex}
        )
        assert shipped.status_code == 201
        code = shipped.json()["code"]
        for status in ("PACKING", "SHIPPED", "DELIVERED"):
            response = await client.patch(f"/api/v1/orders/{code}", json={"status": status})
            assert response.status_code == 200, response.text
        async with session_factory() as session:
            assert (await session.get(ProductSize, second_id)).reserved == 0
            assert (await session.get(ProductSize, second_id)).stock_quantity == 1

    finally:
        await client.aclose()
        await other.aclose()


async def test_size_validation_and_concurrent_last_unit():
    clients = [await member(), await member()]
    try:
        client = clients[0][0]
        product = (await client.get("/api/v1/products/sweater-01")).json()
        sid = product["sizes"][0]["id"]
        foreign = (await client.get("/api/v1/products/order-shirt")).json()
        # A size from another product is rejected even though its ID exists.
        wrong = {
            "product_id": "sweater-01",
            "product_size_id": foreign["sizes"][0]["id"],
            "quantity": 1,
        }
        assert (await client.put("/api/v1/cart", json={"items": [wrong]})).status_code == 409
        async with session_factory.begin() as session:
            size = await session.get(ProductSize, sid)
            size.stock_quantity = size.reserved + 1
        body = await payload(client)
        body["items"][0]["product_size_id"] = sid
        responses = await asyncio.gather(
            *[
                c.post("/api/v1/checkout", json=body, headers={"Idempotency-Key": uuid.uuid4().hex})
                for c, _ in clients
            ]
        )
        assert sorted(r.status_code for r in responses) == [201, 409]
        duplicate = {"product_id": "sweater-01", "product_size_id": sid, "quantity": 1}
        assert (
            await client.put("/api/v1/cart", json={"items": [duplicate, duplicate]})
        ).status_code == 422
    finally:
        for client, _ in clients:
            await client.aclose()
