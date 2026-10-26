"""Operator-only import of reviewed shop records; image bytes stay in memory."""

import argparse
import asyncio
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import (
    CategoryRow,
    DataSource,
    ImportBatch,
    Inventory,
    ProductImage,
    ProductRow,
    ProductSource,
    ProductVariant,
    SellerOffer,
    SourceProduct,
)
from app.infrastructure.product_image_url import inspect_image
from app.infrastructure.seed import add, normalized
from app.infrastructure.sizes import initialize_sizes

SOURCE = "rhodi-user-reviewed"


def validate(record: dict[str, Any], rights_reviewed: bool) -> str:
    if not rights_reviewed:
        raise ValueError("Cần xác nhận quyền sử dụng sản phẩm và ảnh trước khi nhập.")
    image = urlsplit(record["image_url"])
    if (
        image.scheme != "https"
        or image.netloc != "i.postimg.cc"
        or image.query
        or image.fragment
        or len(record["image_url"]) > 180
    ):
        raise ValueError("Chỉ nhận URL ảnh trực tiếp HTTPS từ i.postimg.cc, tối đa 180 ký tự.")
    source = urlsplit(record["source_url"])
    match = re.search(r"-p(\d+)\.html$", source.path)
    if source.scheme != "https" or source.netloc != "rhodi.vn" or not match:
        raise ValueError("Link sản phẩm nguồn không hợp lệ.")
    for field in ("name", "description", "size", "color", "category_id"):
        if not isinstance(record.get(field), str) or not record[field].strip():
            raise ValueError(f"Thiếu trường {field}.")
    for field, minimum in (("price_vnd", 1), ("trial_stock", 0)):
        if type(record.get(field)) is not int or record[field] < minimum:
            raise ValueError(f"{field} phải là số nguyên hợp lệ.")
    return "p" + match[1]


async def import_record(
    session: AsyncSession, record: dict[str, Any], photo: dict[str, Any], *, rights_reviewed: bool
) -> dict[str, Any]:
    external = validate(record, rights_reviewed)
    category = await session.get(CategoryRow, record["category_id"])
    if not category or not category.is_active or category.level != 2:
        raise ValueError("Hãy chọn danh mục lá đang sử dụng.")
    await session.execute(text("SELECT pg_advisory_xact_lock(26102601)"))
    raw_hash = hashlib.sha256(
        json.dumps(record, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    pid = "rhodi-" + external
    old = await session.get(SourceProduct, (SOURCE, external))
    if old:
        if old.raw_hash != raw_hash:
            raise ValueError("Bản ghi đã thay đổi; cần đối chiếu trước khi cập nhật.")
        return {"id": pid, "reused": True}
    stamp = datetime.now(UTC)
    await add(
        session,
        DataSource,
        id=SOURCE,
        name="Rhodi — mẫu do người dùng cung cấp",
        version="shopping-sample-v1",
        license="User-confirmed permission; no open license claimed",
        rights_status="approved",
        allowed_use="User confirmed product/image reuse for local web demo",
        last_checked_at=stamp,
    )
    batch = "shopping-" + raw_hash[:24]
    await add(
        session,
        ImportBatch,
        id=batch,
        source_id=SOURCE,
        started_at=stamp,
        status="completed",
        counts={"created": 1, "rights_reviewed": True},
        errors=[],
    )
    await add(
        session,
        SourceProduct,
        source_id=SOURCE,
        external_id=external,
        raw_json=record,
        raw_hash=raw_hash,
        imported_at=stamp,
        batch_id=batch,
    )
    await add(
        session,
        ProductRow,
        id=pid,
        slug=pid,
        name_vi=record["name"],
        original_name=record["name"],
        description_vi=record["description"],
        category_id=record["category_id"],
        brand_id=None,
        gender="nam",
        publication_status="published",
        verification_status="verified",
        data_profile="real_demo",
        search_text_normalized=normalized(record["name"] + " " + record["description"]),
    )
    await add(
        session,
        ProductSource,
        product_id=pid,
        source_id=SOURCE,
        external_id=external,
        field_provenance={
            "record": "DataShopping.xlsx; operator reviewed source import",
            "source_url": record["source_url"],
            "rights": "Explicit user confirmation in chat, 2026-10-26",
            "price_stock": (
                "Sheet price; random demo stock 5–20 approved by user; source stock missing"
                if record.get("trial_stock_origin")
                else "Copied sheet values for simulated trial; not live merchant stock/price"
            ),
        },
    )
    await add(
        session,
        ProductImage,
        id="image-" + pid,
        product_id=pid,
        storage_key=record["image_url"],
        **photo,
        license_status="approved",
        is_primary=True,
        alt_vi=record["name"],
    )
    await add(
        session,
        ProductVariant,
        id="variant-" + pid,
        product_id=pid,
        sku="TRIAL-" + pid.upper(),
        size=record["size"],
        color=(
            record["color"].lower() if record["color"] != "Chưa có thông tin" else record["color"]
        ),
        option_values={
            "sku_origin": "generated trial identifier",
            "available_sizes": split_options(record["size"]),
            "available_colors": split_options(record["color"]),
            "inventory_scope": "product_trial_capacity_not_per_size",
        },
        status="active",
    )
    await add(
        session,
        SellerOffer,
        id="offer-" + pid,
        product_id=pid,
        variant_id="variant-" + pid,
        seller_id="hoodoomart-trial",
        price_vnd=record["price_vnd"],
        price_kind="demo",
        seller_verified=True,
        active=True,
    )
    await add(
        session,
        Inventory,
        offer_id="offer-" + pid,
        on_hand=record["trial_stock"],
        reserved=0,
        version=1,
    )
    await initialize_sizes(session, pid)
    return {"id": pid, "reused": False}


def split_options(value: str) -> list[str]:
    if value == "Chưa có thông tin":
        return []
    return list(dict.fromkeys(part.strip() for part in value.split(",") if part.strip()))


async def main(rights_reviewed: bool, dry_run: bool = False) -> None:
    payload = json.load(sys.stdin)
    records = payload if isinstance(payload, list) else [payload]
    if not records:
        raise ValueError("Danh sách nhập không được rỗng.")
    identifiers = [validate(record, rights_reviewed) for record in records]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("File có mã sản phẩm nguồn bị trùng.")
    gate = asyncio.Semaphore(3)

    async def photo_for(record: dict[str, Any]) -> dict[str, Any]:
        async with gate:
            return await inspect_image(record["image_url"])

    photos = await asyncio.gather(*(photo_for(record) for record in records))
    try:
        async with session_factory() as session:
            results = [
                await import_record(session, record, photo, rights_reviewed=rights_reviewed)
                for record, photo in zip(records, photos, strict=True)
            ]
            if dry_run:
                await session.rollback()
            else:
                await session.commit()
        result = {
            "dry_run": dry_run,
            "created": sum(not item["reused"] for item in results),
            "reused": sum(item["reused"] for item in results),
            "records": results,
        }
        print(json.dumps(result if isinstance(payload, list) or dry_run else results[0]))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rights-reviewed", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.rights_reviewed, args.dry_run))
