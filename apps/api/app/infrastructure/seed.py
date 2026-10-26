"""Idempotent additive demo seed. Never overwrite modified catalog/stock or erase data."""

import asyncio
import hashlib
import json
import unicodedata
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Table, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import FIXTURE_ROOT
from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import (
    Base,
    CategoryRow,
    DataSource,
    ImportBatch,
    Inventory,
    Order,
    OrderItem,
    ProductAttribute,
    ProductImage,
    ProductRow,
    ProductSource,
    ProductVariant,
    SellerOffer,
    SourceProduct,
    User,
)
from app.infrastructure.sizes import initialize_sizes

STAMP = datetime(2026, 10, 21, tzinfo=UTC)


def normalized(text_value: str) -> str:
    decomposed = unicodedata.normalize("NFD", text_value.lower().replace("đ", "d"))
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())


async def add(session: AsyncSession, model: type[Base], **values: Any) -> None:
    table = model.__table__
    assert isinstance(table, Table)
    await session.execute(insert(table).values(**values).on_conflict_do_nothing())


async def seed(session: AsyncSession) -> dict[str, int]:
    if get_settings().data_profile != "demo_seed":
        raise RuntimeError("Demo seed refused: DATA_PROFILE must be demo_seed")
    fixture = json.loads((FIXTURE_ROOT / "catalog.json").read_text(encoding="utf-8"))
    await session.execute(text("SELECT pg_advisory_xact_lock(2101026)"))
    for sid, rights in [
        ("hoodoomart-original-fixture", "demo"),
        ("quarantined-fixture", "unknown"),
    ]:
        await add(
            session,
            DataSource,
            id=sid,
            name="HoodooMart original simulated fixture",
            version=fixture["version"],
            license="CC0-1.0",
            rights_status=rights,
            allowed_use="demo_seed; original synthetic data and illustrations",
            last_checked_at=STAMP,
        )
        await add(
            session,
            ImportBatch,
            id=f"{sid}-v1",
            source_id=sid,
            started_at=STAMP,
            status="completed",
            counts={"fixture": True},
            errors=[],
        )
    for c in sorted(fixture["categories"], key=lambda c: c["level"]):
        await add(session, CategoryRow, **c)
    for p in fixture["products"]:
        pid, sid = p["id"], p["source_id"]
        raw_hash = hashlib.sha256(
            json.dumps(p, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        stored = await session.scalar(
            select(SourceProduct.raw_hash).where(
                SourceProduct.source_id == sid, SourceProduct.external_id == pid
            )
        )
        if stored is not None and stored != raw_hash:
            raise RuntimeError("Fixture revision changed: use a reviewed migration/import revision")
        image_path = FIXTURE_ROOT / "images" / f"{pid}.svg"
        if hashlib.sha256(image_path.read_bytes()).hexdigest() != p["image_sha256"]:
            raise RuntimeError("Fixture image digest mismatch")
        await add(
            session,
            SourceProduct,
            source_id=sid,
            external_id=pid,
            raw_json=p,
            raw_hash=raw_hash,
            imported_at=STAMP,
            batch_id=f"{sid}-v1",
        )
        await add(
            session,
            ProductRow,
            id=pid,
            slug=p["slug"],
            name_vi=p["name_vi"],
            original_name=p["name_vi"],
            description_vi=p["description_vi"],
            category_id=p["category_id"],
            brand_id=None,
            gender=p["gender"],
            publication_status=p["publication_status"],
            verification_status=p["verification_status"],
            data_profile="demo_seed",
            search_text_normalized=normalized(p["name_vi"]),
            created_at=STAMP,
            updated_at=STAMP,
        )
        await add(
            session,
            ProductSource,
            product_id=pid,
            source_id=sid,
            external_id=pid,
            field_provenance={k: "original_demo_fixture" for k in p},
        )
        for key in ["material", "season"]:
            if key in p:
                await add(
                    session,
                    ProductAttribute,
                    product_id=pid,
                    attribute_key=key,
                    canonical_value=p[key],
                    display_value_vi=p[key],
                    confidence=100,
                    review_status="verified",
                    provenance="original_demo_fixture",
                )
        await add(
            session,
            ProductImage,
            id=f"image-{pid}",
            product_id=pid,
            storage_key=f"/media/{pid}.svg",
            sha256=p["image_sha256"],
            width=500,
            height=560,
            license_status=p["image_license"],
            is_primary=True,
            alt_vi=f"{p['name_vi']} — minh họa mô phỏng",
        )
        await add(
            session,
            ProductVariant,
            id=f"variant-{pid}",
            product_id=pid,
            sku=f"DEMO-{pid}",
            size=p["size"],
            color=p["color"],
            option_values={},
            status="active",
        )
        await add(
            session,
            SellerOffer,
            id=f"offer-{pid}",
            product_id=pid,
            variant_id=f"variant-{pid}",
            seller_id="demo-source",
            price_vnd=p["price_vnd"],
            price_kind=p["price_kind"],
            seller_verified=True,
            active=True,
            updated_at=STAMP,
        )
        await add(
            session,
            Inventory,
            offer_id=f"offer-{pid}",
            on_hand=p["stock"],
            reserved=0,
            version=1,
            updated_at=STAMP,
        )
        await initialize_sizes(session, pid)
    await add(
        session,
        User,
        id="fixture-customer",
        email="fixture-customer@example.invalid",
        password_hash=None,
        is_active=False,
    )
    order = fixture["order"]
    await add(
        session,
        Order,
        id="fixture-order",
        code=order["code"],
        user_id=order["user_id"],
        status=order["status"],
        total_vnd=order["total_vnd"],
        data_profile="demo_seed",
    )
    for item in order["items"]:
        product = next(p for p in fixture["products"] if p["id"] == item["product_id"])
        await add(
            session,
            OrderItem,
            id=f"order-item-{product['id']}",
            order_id="fixture-order",
            product_id=product["id"],
            name_snapshot=product["name_vi"],
            unit_price_vnd=item["price_vnd"],
            quantity=item["quantity"],
        )
    return {
        "fixture_categories": len(fixture["categories"]),
        "fixture_products": len(fixture["products"]),
    }


async def main() -> None:
    try:
        async with session_factory.begin() as session:
            result = await seed(session)
        print(json.dumps(result))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
