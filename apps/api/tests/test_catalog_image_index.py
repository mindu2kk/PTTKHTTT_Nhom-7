import runpy
from pathlib import Path

import pytest
from sqlalchemy import update

from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import ProductImage, ProductRow

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/index_real_images.py"


async def test_index_includes_url_gallery_but_excludes_drafts_and_unapproved_images():
    module = runpy.run_path(str(SCRIPT))
    async with session_factory() as session:
        session.add(
            ProductImage(
                id="index-gallery",
                product_id="sweater-01",
                storage_key="https://i.postimg.cc/test/gallery.jpg",
                sha256="a" * 64,
                width=100,
                height=100,
                license_status="demo",
                is_primary=False,
                alt_vi="Ảnh phụ",
                sort_order=1,
            )
        )
        await session.flush()
        rows = await module["load_public_images"](session, "demo_seed")
        assert "index-gallery" in {row.id for row in rows}
        await session.execute(
            update(ProductImage)
            .where(ProductImage.id == "index-gallery")
            .values(license_status="unknown")
        )
        rows = await module["load_public_images"](session, "demo_seed")
        assert "index-gallery" not in {row.id for row in rows}
        await session.execute(
            update(ProductRow)
            .where(ProductRow.id == "sweater-01")
            .values(publication_status="draft")
        )
        rows = await module["load_public_images"](session, "demo_seed")
        assert all(row.product_id != "sweater-01" for row in rows)
        await session.rollback()
    await engine.dispose()


@pytest.mark.parametrize(
    "key",
    [
        "/media/../secret",
        "/media/catalog/../secret",
        "/media/catalog/..\\secret",
        "file:///etc/passwd",
        "https://localhost/private",
    ],
)
async def test_index_rejects_unsafe_paths_and_hosts(key):
    module = runpy.run_path(str(SCRIPT))
    with pytest.raises(ValueError):
        await module["read_image_content"](key)
