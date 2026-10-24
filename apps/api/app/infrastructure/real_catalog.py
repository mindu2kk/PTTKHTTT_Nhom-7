"""Reviewed ABO staging import. Transactional, additive, no overwrite of user edits."""

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import CATALOG_MEDIA_ROOT
from app.infrastructure.abo_mapping import TYPES
from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import (
    CategoryRow,
    DataSource,
    ImportBatch,
    Inventory,
    ProductAttribute,
    ProductImage,
    ProductRow,
    ProductSource,
    ProductVariant,
    SellerOffer,
    SourceProduct,
)
from app.infrastructure.seed import add, normalized

ROOT = Path(__file__).resolve().parents[4]
SOURCE = "amazon-berkeley-objects"
REVISION = "listings_0-49304dd0edc3aa3d4cb19231927732fc"


def validate_manifest(manifest: dict[str, Any], media: Path = CATALOG_MEDIA_ROOT) -> None:
    from PIL import Image

    rights = json.loads((ROOT / "data/sources/abo-rights.json").read_text(encoding="utf8"))
    qc = json.loads((ROOT / "data/sources/abo-image-qc.json").read_text(encoding="utf8"))
    rejected_photos = {row["source_image_id"] for row in qc["rejected"]}
    if (
        rights["status"] != "approved"
        or manifest.get("license") != "CC-BY-4.0"
        or manifest.get("revision") != REVISION
        or manifest.get("source") != SOURCE
    ):
        raise ValueError("License, source or revision not approved")
    seen, hashes = set(), set()
    for record in manifest["records"]:
        raw = record["raw"]
        if raw.get("main_image_id") in rejected_photos:
            raise ValueError("Primary photo failed recorded visual QC")
        titles = " ".join(
            str(item.get("value", ""))
            for item in raw.get("item_name", [])
            if item.get("language_tag", "").startswith("en")
        )
        if re.search(r"\b(swatch|sample|replacement)\b", titles, re.IGNORECASE):
            raise ValueError("Source is a sample/replacement, not the mapped whole product")
        external = f"{raw.get('domain_name', '')}:{raw.get('item_id', '')}"
        expected = "abo-" + hashlib.sha256(external.encode()).hexdigest()[:20]
        if (
            not raw.get("item_id")
            or not raw.get("domain_name")
            or external != record["external_id"]
            or record["id"] != expected
            or external in seen
        ):
            raise ValueError("Missing, duplicate or mismatched external product ID")
        seen.add(external)
        if record["group"] not in {"nam", "nu", "dien-tu", "gia-dung"} or not record[
            "category_id"
        ].startswith("abo-"):
            raise ValueError("Unreviewed category mapping")
        kind = raw.get("product_type", [{}])[0].get("value")
        if kind in {"SHOES", "BOOT", "SANDAL"}:
            gender = (
                "nu"
                if re.search(r"\bwomen(?:'s|s)?\b", titles, re.IGNORECASE)
                else "nam"
                if re.search(r"\bmen(?:'s|s)?\b", titles, re.IGNORECASE)
                else None
            )
            expected_mapping = (gender, "abo-giay-" + str(gender))
        elif kind in TYPES:
            expected_mapping = (TYPES[kind][0], "abo-" + TYPES[kind][1])
        else:
            raise ValueError("Unsupported source product type")
        if (record["group"], record["category_id"]) != expected_mapping:
            raise ValueError("Category does not match reviewed source type mapping")
        if (
            not record["images"]
            or not record["images"][0]["primary"]
            or record["images"][0]["source_image_id"] != raw.get("main_image_id")
        ):
            raise ValueError("Primary photo does not belong to source product")
        if record["images"][0]["source_sha256"] in hashes:
            raise ValueError("Duplicate primary photo")
        hashes.add(record["images"][0]["source_sha256"])
        for n, photo in enumerate(record["images"]):
            if n and photo["source_image_id"] not in raw.get("other_image_id", []):
                raise ValueError("Additional photo does not belong to source product")
            if photo["url"] != f"/media/catalog/{expected}-{n}.webp":
                raise ValueError("Unsafe or mismatched local image path")
            file = media / f"{expected}-{n}.webp"
            if hashlib.sha256(file.read_bytes()).hexdigest() != photo["sha256"]:
                raise ValueError("Image hash mismatch")
            with Image.open(file) as image:
                image.verify()
        if (
            type(record["price_vnd"]) is not int
            or record["price_vnd"] <= 0
            or record["demo_capacity"] != 5
        ):
            raise ValueError("Invalid separately simulated offer")


async def load_catalog(
    session: AsyncSession, manifest: dict[str, Any], media: Path = CATALOG_MEDIA_ROOT
) -> dict[str, Any]:
    validate_manifest(manifest, media)
    await session.execute(text("SELECT pg_advisory_xact_lock(2101028)"))
    stamp = datetime.now(UTC)
    batch_hash = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    batch = "abo-m8-" + batch_hash[:24]
    await add(
        session,
        DataSource,
        id=SOURCE,
        name="Amazon Berkeley Objects — Amazon.com",
        version=REVISION,
        license="CC-BY-4.0",
        rights_status="approved",
        allowed_use=(
            "CC BY 4.0 data/photos; attribution in /sources. "
            "Original records + separate simulated offers; no endorsement."
        ),
        last_checked_at=stamp,
    )
    stored_source = await session.get(DataSource, SOURCE)
    if (
        not stored_source
        or stored_source.rights_status != "approved"
        or stored_source.version != REVISION
        or stored_source.license != "CC-BY-4.0"
    ):
        raise ValueError("Stored source rights/revision revoked or changed")
    await add(
        session,
        ImportBatch,
        id=batch,
        source_id=SOURCE,
        started_at=stamp,
        status="completed",
        counts={"validated": len(manifest["records"])},
        errors=manifest["errors"],
    )
    roots = {
        "nam": ("thoi-trang-nam", "Thời trang nam"),
        "nu": ("thoi-trang-nu", "Thời trang nữ"),
        "dien-tu": ("dien-tu", "Điện tử"),
        "gia-dung": ("gia-dung", "Gia dụng"),
    }
    for order, (rid, name) in enumerate(roots.values()):
        await add(
            session,
            CategoryRow,
            id=rid,
            parent_id=None,
            slug=rid,
            name_vi=name,
            level=0,
            sort_order=order,
        )
    created = reused = 0
    for record in manifest["records"]:
        pid, raw = record["id"], record["raw"]
        raw_hash = hashlib.sha256(
            json.dumps(raw, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        stored = await session.get(SourceProduct, (SOURCE, record["external_id"]))
        if stored is not None:
            if stored.raw_hash != raw_hash:
                raise ValueError("Source revision changed; reviewed reconciliation required")
            reused += 1
            continue
        group = record["group"]
        parent = "abo-group-" + group
        await add(
            session,
            CategoryRow,
            id=parent,
            parent_id=roots[group][0],
            slug=parent,
            name_vi={
                "nam": "Giày và phụ kiện nam",
                "nu": "Giày và phụ kiện nữ",
                "dien-tu": "Thiết bị và phụ kiện",
                "gia-dung": "Đồ dùng trong nhà",
            }[group],
            level=1,
            sort_order=0,
        )
        await add(
            session,
            CategoryRow,
            id=record["category_id"],
            parent_id=parent,
            slug=record["category_id"],
            name_vi={"nam": "Giày nam", "nu": "Giày nữ"}.get(group, record["category_name"]),
            level=2,
            sort_order=0,
        )
        await add(
            session,
            SourceProduct,
            source_id=SOURCE,
            external_id=record["external_id"],
            raw_json=raw,
            raw_hash=raw_hash,
            imported_at=stamp,
            batch_id=batch,
        )
        await add(
            session,
            ProductRow,
            id=pid,
            slug=pid,
            name_vi=record["name_vi"],
            original_name=record["original_name"],
            description_vi=record["description_vi"],
            category_id=record["category_id"],
            brand_id=record["brand"],
            gender=record["gender"],
            publication_status="published",
            verification_status="verified",
            data_profile="real_demo",
            search_text_normalized=normalized(record["name_vi"] + " " + record["original_name"]),
            created_at=stamp,
            updated_at=stamp,
        )
        await add(
            session,
            ProductSource,
            product_id=pid,
            source_id=SOURCE,
            external_id=record["external_id"],
            field_provenance={
                "name": "Vietnamese type/brand/model mapping; original_name retained",
                "images": (
                    "ABO main_image_id/other_image_id -> official images.csv -> original asset"
                ),
                "price_vnd": "HoodooMart category-based simulated offer; not source price",
                "inventory": "Trial capacity5, not merchant stock",
                "mapping_revision": "m8-v1",
            },
        )
        if record["material"]:
            await add(
                session,
                ProductAttribute,
                product_id=pid,
                attribute_key="material",
                canonical_value=record["material"],
                display_value_vi=record["material"],
                confidence=100,
                review_status="verified",
                provenance="ABO material; original language retained",
            )
        for n, photo in enumerate(record["images"]):
            await add(
                session,
                ProductImage,
                id=f"image-{pid}-{n}",
                product_id=pid,
                storage_key=photo["url"],
                sha256=photo["sha256"],
                width=photo["width"],
                height=photo["height"],
                license_status="approved",
                is_primary=n == 0,
                alt_vi=f"{record['name_vi']} — ảnh ABO {photo['source_image_id']}"[:250],
            )
        await add(
            session,
            ProductVariant,
            id=f"variant-{pid}",
            product_id=pid,
            sku=f"ABO-{record['external_id']}",
            size="Phiên bản nguồn",
            color=record["color"],
            option_values={"source_product": record["external_id"]},
            status="active",
        )
        await add(
            session,
            SellerOffer,
            id=f"offer-{pid}",
            product_id=pid,
            variant_id=f"variant-{pid}",
            seller_id="hoodoomart-trial",
            price_vnd=record["price_vnd"],
            price_kind="demo",
            seller_verified=True,
            active=True,
            updated_at=stamp,
        )
        await add(
            session,
            Inventory,
            offer_id=f"offer-{pid}",
            on_hand=record["demo_capacity"],
            reserved=0,
            version=1,
            updated_at=stamp,
        )
        created += 1
    return {
        "created": created,
        "reused": reused,
        "batch": batch,
        "profile": "real_demo",
        "source": SOURCE,
        "records": len(manifest["records"]),
    }


def ensure_reviewed(manifest: dict[str, Any]) -> None:
    selection = json.loads((ROOT / "data/sources/abo-selection.json").read_text(encoding="utf8"))
    if selection["revision"] != REVISION or any(
        record["external_id"] not in selection["external_ids"] for record in manifest["records"]
    ):
        raise ValueError("New records need recorded visual/provenance review before publication")


async def import_catalog(dry_run: bool = True) -> dict[str, Any]:
    manifest = json.loads((ROOT / "data/private/m8/validated.json").read_text(encoding="utf8"))
    try:
        validate_manifest(manifest)
        if dry_run:
            return {
                "dry_run": True,
                "valid_records": len(manifest["records"]),
                "images": sum(len(r["images"]) for r in manifest["records"]),
            }
        ensure_reviewed(manifest)
        async with session_factory.begin() as session:
            return await load_catalog(session, manifest)
    finally:
        await engine.dispose()
