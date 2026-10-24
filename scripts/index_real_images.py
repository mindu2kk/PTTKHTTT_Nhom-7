"""Incremental offline OpenCLIP index for approved ABO photographs only."""

import asyncio
import hashlib
import json
import time
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.dependencies import CATALOG_MEDIA_ROOT
from app.infrastructure.media import CLIP_REVISION
from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import (
    DataSource,
    ImageEmbedding,
    ProductImage,
    ProductRow,
    ProductSource,
)


async def main():
    started = time.perf_counter()
    encoded = skipped = 0
    first = None
    async with session_factory.begin() as session:
        rows = (
            await session.scalars(
                select(ProductImage)
                .join(ProductRow, ProductRow.id == ProductImage.product_id)
                .join(ProductSource, ProductSource.product_id == ProductRow.id)
                .join(DataSource, DataSource.id == ProductSource.source_id)
                .where(
                    ProductRow.data_profile == "real_demo",
                    ProductRow.publication_status == "published",
                    ProductRow.verification_status == "verified",
                    ProductImage.license_status == "approved",
                    DataSource.id == "amazon-berkeley-objects",
                    DataSource.rights_status == "approved",
                )
                .order_by(ProductImage.id)
            )
        ).all()
        async with httpx.AsyncClient(
            base_url=get_settings().inference_url, timeout=60, trust_env=False
        ) as client:
            for image in rows:
                raw = (CATALOG_MEDIA_ROOT / Path(image.storage_key).name).read_bytes()
                if hashlib.sha256(raw).hexdigest() != image.sha256:
                    raise ValueError(
                        "Approved image content changed; import review required"
                    )
                old = await session.get(
                    ImageEmbedding, (image.id, "OpenCLIP ViT-B/32", CLIP_REVISION)
                )
                if old is not None and old.content_hash == image.sha256:
                    skipped += 1
                    continue
                response = await client.post(
                    "/encode", content=raw, headers={"Content-Type": "image/webp"}
                )
                response.raise_for_status()
                result = response.json()
                if (
                    result["model_revision"] != CLIP_REVISION
                    or result["model_name"] != "OpenCLIP ViT-B/32"
                    or len(result["vector"]) != 512
                ):
                    raise ValueError("Incompatible model output")
                if first is None:
                    first = {
                        key: result.get(key)
                        for key in ["model_load_ms", "rss_mib", "inference_ms"]
                    }
                statement = insert(ImageEmbedding).values(
                    image_id=image.id,
                    model_name=result["model_name"],
                    model_revision=CLIP_REVISION,
                    content_hash=image.sha256,
                    embedding=result["vector"],
                )
                await session.execute(
                    statement.on_conflict_do_update(
                        index_elements=["image_id", "model_name", "model_revision"],
                        set_={
                            "content_hash": image.sha256,
                            "embedding": result["vector"],
                        },
                    )
                )
                encoded += 1
                if encoded % 25 == 0:
                    print(f"Encoded {encoded}; skipped {skipped}", flush=True)
    await engine.dispose()
    report = {
        "encoded": encoded,
        "skipped_unchanged": skipped,
        "approved_images": len(rows),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "revision": CLIP_REVISION,
        "first_call": first,
        "scope": "Offline index of all approved real_demo photos, primary and gallery; exact filtered vector retrieval aggregates by product",
    }
    directory = Path("docs/evidence/m8")
    directory.mkdir(parents=True, exist_ok=True)
    (directory / ("index-replay.json" if encoded == 0 else "index.json")).write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
