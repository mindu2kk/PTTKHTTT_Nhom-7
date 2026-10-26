import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.commerce import Actor, BusinessError
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.commerce import SqlCommerceStore
from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import (
    CategoryRow,
    DataSource,
    Inventory,
    ProductImage,
    ProductSize,
    UserRole,
)
from app.infrastructure.real_catalog import SOURCE, load_catalog

from .test_commerce import cleanup, member  # noqa: F401
from .test_real_catalog import sample as real_catalog_sample  # noqa: F401,F811


async def test_admin_create_edit_and_stock_validation_over_http():
    client, owner = await member()
    customer, _ = await member()
    try:
        async with session_factory.begin() as session:
            session.add(UserRole(user_id=owner, role="admin"))
        images = (await client.get("/api/v1/manage/images")).json()["items"]
        draft = {
            "name": "Áo quản trị thử nghiệm",
            "description": "Thông tin nguyên bản trong bộ kiểm thử quản trị",
            "category_id": "ao-len-nam",
            "image_id": images[0]["id"],
            "price_vnd": 200000,
            "stock": 7,
            "color": "đen",
            "material": "cotton",
            "brand": "Hoodoo",
            "size": "M, L",
            "sizes": [{"size": "M", "stock": 4}, {"size": "L", "stock": 3}],
            "original_data_confirmed": True,
        }
        assert (await customer.post("/api/v1/manage/products", json=draft)).status_code == 403
        response = await client.post("/api/v1/manage/products", json=draft)
        assert response.status_code == 201, response.text
        pid = response.json()["id"]
        assert (await client.get(f"/api/v1/products/{pid}")).status_code == 404
        assert (await client.post(f"/api/v1/manage/products/{pid}/publish")).status_code == 200
        edit = {
            key: value
            for key, value in draft.items()
            if key not in {"size", "original_data_confirmed"}
        }
        edit.update(
            name="Áo quản trị đã chỉnh sửa",
            description="Mô tả mới có thể tìm kiếm trong catalog",
            stock=9,
            sizes=[{"size": "M", "stock": 5}, {"size": "XL", "stock": 4}],
        )
        assert (
            await customer.patch(f"/api/v1/manage/products/{pid}", json=edit)
        ).status_code == 403
        response = await client.patch(f"/api/v1/manage/products/{pid}", json=edit)
        assert response.status_code == 200, response.text
        product = (await client.get(f"/api/v1/products/{pid}")).json()
        assert (
            product["name_vi"] == edit["name"] and product["description_vi"] == edit["description"]
        )
        assert product["brand"] == "Hoodoo" and product["available_quantity"] == 9
        assert {s["size"]: s["available_quantity"] for s in product["sizes"]} == {
            "M": 5,
            "L": 0,
            "XL": 4,
        }
        bad = {**edit, "stock": 8}
        assert (await client.patch(f"/api/v1/manage/products/{pid}", json=bad)).status_code == 422
        bad = {**edit, "sizes": [{"size": "M", "stock": 5}, {"size": "M", "stock": 4}]}
        assert (await client.patch(f"/api/v1/manage/products/{pid}", json=bad)).status_code == 422
        bad = {**edit, "image_id": "unapproved-image"}
        assert (await client.patch(f"/api/v1/manage/products/{pid}", json=bad)).status_code == 422
        assert (await client.get(f"/api/v1/products/{pid}")).json() == product
    finally:
        await client.aclose()
        await customer.aclose()


async def test_real_demo_admin_crud_preserves_rights_reservations_and_profiles(real_catalog_sample):  # noqa: F811
    manifest, directory = real_catalog_sample
    async with engine.connect() as connection:
        transaction = await connection.begin()
        factory = async_sessionmaker(
            connection, expire_on_commit=False, join_transaction_mode="create_savepoint"
        )
        try:
            async with factory.begin() as session:
                await load_catalog(session, manifest, directory)
                await session.execute(
                    update(CategoryRow)
                    .where(CategoryRow.id == "abo-tai-nghe")
                    .values(is_active=True)
                )
                image = await session.scalar(
                    select(ProductImage).where(
                        ProductImage.product_id == manifest["records"][0]["id"],
                        ProductImage.is_primary.is_(True),
                    )
                )
                image_id = image.id
            actor = Actor("fixture-customer", "fixture-customer@example.invalid", ("admin",), False)
            store = SqlCommerceStore(factory, "real_demo")
            body = {
                "name": "Mặt hàng mới do admin tạo",
                "description": "Nội dung gốc do quản trị viên xác nhận quyền sử dụng",
                "category_id": "abo-tai-nghe",
                "image_id": image_id,
                "price_vnd": 250000,
                "stock": 4,
                "color": "đen",
                "material": "vải",
                "size": "M, L",
                "sizes": [{"size": "M", "stock": 2}, {"size": "L", "stock": 2}],
                "original_data_confirmed": True,
            }
            created = await store.manage(actor, "create", body)
            pid = created["id"]
            assert pid.startswith("hoodoo-")
            assert (await store.manage(actor, "create", body))["id"] == pid
            async with factory() as session:
                assert await SqlCatalogRepository(session, "real_demo").get_product(pid) is None
            await store.manage(actor, "publish", {"id": pid})
            async with factory() as session:
                product = await SqlCatalogRepository(session, "real_demo").get_product(pid)
                assert product and product.available_quantity == 4
                assert await SqlCatalogRepository(session, "demo_seed").get_product(pid) is None
                size = await session.scalar(
                    select(ProductSize).where(
                        ProductSize.product_id == pid, ProductSize.size == "M"
                    )
                )
                sid = size.id
            order = await store.checkout(
                actor,
                "admin-size-checkout",
                {
                    "items": [
                        {
                            "product_id": pid,
                            "product_size_id": sid,
                            "quantity": 1,
                            "expected_price_vnd": 250000,
                        }
                    ],
                    "method": "cod",
                    "address": {},
                },
            )
            edit = {
                "id": pid,
                "price_vnd": 260000,
                "stock": 4,
                "name": "Mặt hàng cập nhật",
                "sizes": [{"size": "M", "stock": 0}, {"size": "L", "stock": 4}],
            }
            with pytest.raises(BusinessError) as error:
                await store.manage(actor, "update", edit)
            assert error.value.status == 409
            async with factory() as session:
                assert (await session.get(ProductSize, sid)).stock_quantity == 2
                assert (await session.get(Inventory, "offer-" + pid)).on_hand == 4
            await store.transition(actor, order["code"], "CANCELLED")
            await store.manage(actor, "update", edit)
            row = next(
                row for row in (await store.manage(actor, "list", {}))["items"] if row["id"] == pid
            )
            assert row["name"] == "Mặt hàng cập nhật" and row["description"] == body["description"]
            assert (await store.manage(actor, "list", {}))["read_only"] is False
            with pytest.raises(BusinessError) as error:
                await store.manage(actor, "archive", {"id": "sweater-01"})
            assert error.value.status == 404
            # Revoking the copied photo's original source must hide the new product as well.
            async with factory.begin() as session:
                await session.execute(
                    update(DataSource)
                    .where(DataSource.id == SOURCE)
                    .values(rights_status="unknown")
                )
            async with factory() as session:
                assert await SqlCatalogRepository(session, "real_demo").get_product(pid) is None
            with pytest.raises(BusinessError) as error:
                await store.manage(
                    actor, "create", {**body, "name": "Không được dùng nguồn đã thu hồi"}
                )
            assert error.value.status == 422
        finally:
            await transaction.rollback()
    await engine.dispose()


async def test_admin_direct_url_requires_permission_and_rejects_bad_images(monkeypatch):
    from app.infrastructure import commerce

    calls = []

    async def photo(url):
        calls.append(url)
        if url.endswith("broken.png"):
            raise ValueError("Invalid image bytes")
        return {"width": 100, "height": 100, "sha256": "b" * 64}

    monkeypatch.setattr(commerce, "inspect_image", photo)
    client, owner = await member()
    try:
        async with session_factory.begin() as session:
            session.add(UserRole(user_id=owner, role="admin"))
        body = {
            "name": "Mặt hàng dùng URL ảnh",
            "description": "Thông tin gốc cho kiểm thử ảnh URL trực tiếp",
            "category_id": "ao-len-nam",
            "price_vnd": 120000,
            "stock": 2,
            "color": "đen",
            "material": "cotton",
            "size": "F",
            "sizes": [{"size": "F", "stock": 2}],
            "image_url": "https://i.postimg.cc/test/photo.png",
            "image_rights_confirmed": True,
            "original_data_confirmed": True,
        }
        assert (
            await client.post(
                "/api/v1/manage/products", json={**body, "image_rights_confirmed": False}
            )
        ).status_code == 422
        assert (
            await client.post(
                "/api/v1/manage/products",
                json={**body, "image_url": "https://127.0.0.1/private.png"},
            )
        ).status_code == 422
        assert calls == []
        created = await client.post("/api/v1/manage/products", json=body)
        assert created.status_code == 201, created.text
        pid = created.json()["id"]
        assert (await client.post(f"/api/v1/manage/products/{pid}/publish")).status_code == 200
        product = (await client.get(f"/api/v1/products/{pid}")).json()
        assert product["image_url"] == body["image_url"]
        edit = {"price_vnd": 130000, "stock": 2, "image_url": "https://i.postimg.cc/test/new.png"}
        assert (await client.patch(f"/api/v1/manage/products/{pid}", json=edit)).status_code == 422
        edit["image_rights_confirmed"] = True
        assert (await client.patch(f"/api/v1/manage/products/{pid}", json=edit)).status_code == 200
        updated = (await client.get(f"/api/v1/products/{pid}")).json()
        assert updated["image_url"] == edit["image_url"]
        assert (
            await client.patch(
                f"/api/v1/manage/products/{pid}",
                json={**edit, "image_url": "https://i.postimg.cc/test/broken.png"},
            )
        ).status_code == 422
        assert (await client.get(f"/api/v1/products/{pid}")).json() == updated
    finally:
        await client.aclose()


async def test_admin_gallery_order_removal_and_bad_secondary_rollback(monkeypatch):
    import hashlib

    from app.infrastructure import commerce

    async def inspect(url):
        if "broken" in url:
            raise ValueError("Invalid photo")
        return {"width": 32, "height": 32, "sha256": hashlib.sha256(url.encode()).hexdigest()}

    monkeypatch.setattr(commerce, "inspect_image", inspect)
    client, owner = await member()
    try:
        async with session_factory.begin() as session:
            session.add(UserRole(user_id=owner, role="admin"))
        urls = ["https://i.postimg.cc/test/" + name + ".png" for name in ("one", "two", "three")]
        body = {
            "name": "Mặt hàng nhiều ảnh",
            "description": "Mô tả nguyên bản cho sản phẩm nhiều ảnh",
            "category_id": "ao-len-nam",
            "price_vnd": 150000,
            "stock": 3,
            "color": "đen",
            "material": "cotton",
            "size": "F",
            "sizes": [{"size": "F", "stock": 3}],
            "image_urls": urls,
            "image_rights_confirmed": True,
            "original_data_confirmed": True,
        }
        response = await client.post("/api/v1/manage/products", json=body)
        assert response.status_code == 201, response.text
        pid = response.json()["id"]
        assert (await client.post(f"/api/v1/manage/products/{pid}/publish")).status_code == 200
        product = (await client.get(f"/api/v1/products/{pid}")).json()
        assert product["image_url"] == urls[0]
        assert [image["url"] for image in product["images"]] == urls
        edit = {
            "stock": 3,
            "price_vnd": 150000,
            "image_urls": [urls[2], urls[0], urls[1]],
            "image_rights_confirmed": True,
        }
        assert (await client.patch(f"/api/v1/manage/products/{pid}", json=edit)).status_code == 200
        product = (await client.get(f"/api/v1/products/{pid}")).json()
        assert product["image_url"] == urls[2]
        assert [image["url"] for image in product["images"]] == edit["image_urls"]
        edit["image_urls"] = [urls[1], urls[0]]
        assert (await client.patch(f"/api/v1/manage/products/{pid}", json=edit)).status_code == 200
        product = (await client.get(f"/api/v1/products/{pid}")).json()
        assert [image["url"] for image in product["images"]] == edit["image_urls"]
        bad = {**edit, "image_urls": [urls[1], "https://i.postimg.cc/test/broken.png"]}
        assert (await client.patch(f"/api/v1/manage/products/{pid}", json=bad)).status_code == 422
        assert (await client.get(f"/api/v1/products/{pid}")).json() == product
        assert (
            await client.patch(
                f"/api/v1/manage/products/{pid}", json={**edit, "image_urls": [urls[0], urls[0]]}
            )
        ).status_code == 422
        assert (
            await client.patch(
                f"/api/v1/manage/products/{pid}", json={**edit, "image_urls": urls * 4}
            )
        ).status_code == 422
    finally:
        await client.aclose()
