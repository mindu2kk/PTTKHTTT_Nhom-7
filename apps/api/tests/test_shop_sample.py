import io
import json

import pytest
from sqlalchemy import func, select, update

from app.domain.catalog import CatalogFilter
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import (
    CategoryRow,
    DataSource,
    Inventory,
    ProductRow,
    ProductSource,
    ProductVariant,
)
from app.infrastructure.shop_sample import SOURCE, import_record


async def test_page_import_records_actual_provenance_and_preserves_existing_stock():
    record = {
        "name": "Polo dữ liệu kiểm thử gốc",
        "description": "Dữ liệu gốc dành riêng cho kiểm thử nhập theo trang nguồn.",
        "category_id": "nam-polo",
        "size": "M, L, XL",
        "color": "Be nhạt, Xám nhạt, Xám, Nâu, Be, Trắng, Đen",
        "price_vnd": 300000,
        "trial_stock": 10,
        "image_url": "https://pos.nvncdn.com/afec53-228676/ps/test-polo.jpg?v=1790932084",
        "source_url": "https://rhodi.vn/test-p9900010.html",
        "record_origin": "Rhodi product page snapshot; not an Excel row",
        "price_stock_provenance": "Observed page price; local demo capacity, not merchant stock",
    }
    photo = {"width": 640, "height": 800, "sha256": "b" * 64}
    async with session_factory() as session:
        try:
            await session.execute(
                update(CategoryRow).where(CategoryRow.id.like("nam%")).values(is_active=True)
            )
            original = await session.get(Inventory, "offer-sweater-01")
            before = (original.on_hand, original.reserved, original.version)
            result = await import_record(session, record, photo, rights_reviewed=True)
            source = await session.get(ProductSource, (result["id"], SOURCE))
            assert source.field_provenance["record"] == record["record_origin"]
            assert source.field_provenance["price_stock"] == record["price_stock_provenance"]
            product = await SqlCatalogRepository(session, "real_demo").get_product(result["id"])
            assert product and product.image_url == record["image_url"]
            assert product.price_vnd == 300000 and product.available_quantity == 10
            assert product.color == "Nhiều màu"
            variant = await session.get(ProductVariant, "variant-" + result["id"])
            assert variant.option_values["available_colors"] == [
                "Be nhạt",
                "Xám nhạt",
                "Xám",
                "Nâu",
                "Be",
                "Trắng",
                "Đen",
            ]
            assert sum(s["available_quantity"] for s in product.sizes) == 10
            assert (original.on_hand, original.reserved, original.version) == before
            assert (await import_record(session, record, photo, rights_reviewed=True))["reused"]
            with pytest.raises(ValueError, match="quyền"):
                await import_record(session, record, photo, rights_reviewed=False)
        finally:
            await session.rollback()
    await engine.dispose()


async def test_bulk_dry_run_and_invalid_category_roll_back(monkeypatch, capsys):
    from app.infrastructure import shop_sample

    records = [
        {
            "name": "Mẫu kiểm thử nhập nhiều",
            "description": "Dữ liệu test gốc",
            "category_id": "ao-len-nam",
            "size": "M, L, XL",
            "color": "Trắng, Đen",
            "price_vnd": 100000,
            "trial_stock": 9,
            "image_url": "https://i.postimg.cc/test/original.jpg",
            "source_url": f"https://rhodi.vn/test-p990000{n}.html",
        }
        for n in (2, 3)
    ]

    async def fake_image(url):
        return {"width": 100, "height": 100, "sha256": "a" * 64}

    monkeypatch.setattr(shop_sample, "inspect_image", fake_image)
    async with session_factory() as session:
        before = await session.scalar(select(func.count()).select_from(ProductRow))
    monkeypatch.setattr(shop_sample.sys, "stdin", io.StringIO(json.dumps(records)))
    await shop_sample.main(True, dry_run=True)
    assert json.loads(capsys.readouterr().out)["created"] == 2
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ProductRow)) == before
    records[1]["category_id"] = "missing-category"
    monkeypatch.setattr(shop_sample.sys, "stdin", io.StringIO(json.dumps(records)))
    with pytest.raises(ValueError, match="danh mục"):
        await shop_sample.main(True)
    async with session_factory() as session:
        assert await session.scalar(select(func.count()).select_from(ProductRow)) == before
    await engine.dispose()


async def test_reviewed_sample_replay_visibility_and_revocation():
    record = {
        "name": "Áo sơ mi kiểm thử",
        "description": "Dữ liệu mô phỏng unit test",
        "category_id": "nam-ao-so-mi",
        "size": "L",
        "color": "Trắng",
        "price_vnd": 260000,
        "trial_stock": 8,
        "image_url": "https://i.postimg.cc/test/original.jpg",
        "source_url": "https://rhodi.vn/test-p9900001.html",
    }
    photo = {"width": 100, "height": 100, "sha256": "a" * 64}
    async with session_factory() as session:
        try:
            await session.execute(
                update(CategoryRow).where(CategoryRow.id.like("nam%")).values(is_active=True)
            )
            before = await session.scalar(select(func.count()).select_from(ProductRow))
            result = await import_record(session, record, photo, rights_reviewed=True)
            pid = result["id"]
            assert not result["reused"]
            repository = SqlCatalogRepository(session, "real_demo")
            product = await repository.get_product(pid)
            assert product and product.image_url == record["image_url"]
            assert product.images[0]["url"] == record["image_url"]
            assert product.size == "L" and product.available_quantity == 8
            assert product.rights_status == "approved" and product.price_kind == "demo"
            assert await SqlCatalogRepository(session, "demo_seed").get_product(pid) is None
            await session.execute(
                update(Inventory).where(Inventory.offer_id == "offer-" + pid).values(on_hand=5)
            )
            assert (await import_record(session, record, photo, rights_reviewed=True))["reused"]
            assert (await repository.get_product(pid)).available_quantity == 5
            assert await session.scalar(select(func.count()).select_from(ProductRow)) == before + 1
            with pytest.raises(ValueError, match="thay đổi"):
                await import_record(
                    session, {**record, "price_vnd": 300000}, photo, rights_reviewed=True
                )
            await session.execute(
                update(DataSource).where(DataSource.id == SOURCE).values(rights_status="restricted")
            )
            assert await repository.get_product(pid) is None
            assert (await repository.list_products(CatalogFilter(category="nam-ao-so-mi")))[1] == 0
        finally:
            await session.rollback()
    await engine.dispose()
