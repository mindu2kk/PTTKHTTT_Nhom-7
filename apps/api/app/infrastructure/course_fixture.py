"""Explicit, guarded additive provenance import; preserves original v1 raw records."""

import asyncio
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import (
    DataSource,
    ImportBatch,
    ProductSource,
    SellerOffer,
    SourceProduct,
)

PATH = Path(__file__).resolve().parents[4] / "benchmarks/fixtures/course-v2.json"
SOURCE = "course-demo-v2"


async def apply_course_v2(s: AsyncSession) -> dict[str, int]:
    data = json.loads(PATH.read_text(encoding="utf8"))
    now = datetime.now(UTC)
    existing = await s.get(DataSource, SOURCE)
    offers = []
    for record in data["updates"]:
        offer = await s.scalar(
            select(SellerOffer)
            .where(SellerOffer.product_id == record["product_id"])
            .with_for_update()
        )
        expected = record["price_vnd"] if existing else record["expected_original_vnd"]
        if (
            not offer
            or offer.seller_id != "demo-source"
            or offer.price_kind != "demo"
            or offer.price_vnd != expected
        ):
            raise RuntimeError(
                "Course import refused: fixture offer differs from its expected revision; "
                "user edits preserved."
            )
        offers.append((offer, record))
    if existing:
        return {"updated": 0, "already_applied": 2}
    s.add(
        DataSource(
            id=SOURCE,
            name="Hiệu chỉnh dữ liệu mô phỏng theo slide",
            version=data["version"],
            license=data["license"],
            rights_status="demo",
            allowed_use=data["source"],
            last_checked_at=now,
        )
    )
    await s.flush()
    s.add(
        ImportBatch(
            id=SOURCE,
            source_id=SOURCE,
            started_at=now,
            status="approved",
            counts={"updated": 2},
            errors=[],
        )
    )
    await s.flush()
    for offer, record in offers:
        raw = json.dumps(record, sort_keys=True, ensure_ascii=False)
        s.add(
            SourceProduct(
                source_id=SOURCE,
                external_id=record["product_id"],
                raw_json=record,
                raw_hash=hashlib.sha256(raw.encode()).hexdigest(),
                imported_at=now,
                batch_id=SOURCE,
            )
        )
        await s.flush()
        s.add(
            ProductSource(
                product_id=record["product_id"],
                source_id=SOURCE,
                external_id=record["product_id"],
                field_provenance={
                    "price_vnd": "active demo offer correction; course slide p53; v1 raw retained"
                },
            )
        )
        offer.price_vnd = record["price_vnd"]
        offer.updated_at = now
    return {"updated": 2, "already_applied": 0}


async def main() -> None:
    try:
        async with session_factory.begin() as s:
            result = await apply_course_v2(s)
        print(json.dumps(result))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
