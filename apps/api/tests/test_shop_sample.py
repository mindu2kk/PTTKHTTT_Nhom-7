import io
import json

import pytest
from sqlalchemy import func, select, update

from app.domain.catalog import CatalogFilter
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import CategoryRow, DataSource, Inventory, ProductRow
from app.infrastructure.shop_sample import SOURCE, import_record


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
