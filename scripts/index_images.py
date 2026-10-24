"""Offline original gallery encoding into exact PostgreSQL pgvector. Never called by search."""

import asyncio
import hashlib
import json
import time
from pathlib import Path

import fitz
import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.dependencies import FIXTURE_ROOT
from app.domain.catalog import CatalogFilter
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.database import engine, session_factory
from app.infrastructure.media import CLIP_REVISION
from app.infrastructure.models import ImageEmbedding, ProductImage


async def main():
    start = time.perf_counter()
    indexed = 0
    first = None
    async with session_factory.begin() as session:
        repository = SqlCatalogRepository(session, get_settings().data_profile)
        page = 1
        async with httpx.AsyncClient(
            base_url=get_settings().inference_url, timeout=60, trust_env=False
        ) as client:
            while True:
                products, total = await repository.list_products(
                    CatalogFilter(page=page, page_size=1000)
                )
                for product in products:
                    row = await session.scalar(
                        select(ProductImage).where(
                            ProductImage.product_id == product.id
                        )
                    )
                    if row is None:
                        continue
                    filename = Path(row.storage_key).name
                    source = FIXTURE_ROOT / "images" / filename
                    raw = source.read_bytes()
                    assert hashlib.sha256(raw).hexdigest() == row.sha256
                    if source.suffix == ".svg":
                        with fitz.open(stream=raw, filetype="svg") as doc:
                            raw = (
                                doc[0]
                                .get_pixmap(matrix=fitz.Matrix(0.8, 0.8))
                                .tobytes("png")
                            )
                    response = await client.post(
                        "/encode", content=raw, headers={"Content-Type": "image/png"}
                    )
                    response.raise_for_status()
                    encoded = response.json()
                    assert (
                        encoded["model_revision"] == CLIP_REVISION
                        and len(encoded["vector"]) == 512
                    )
                    if first is None:
                        first = encoded
                    statement = insert(ImageEmbedding).values(
                        image_id=row.id,
                        model_name=encoded["model_name"],
                        model_revision=CLIP_REVISION,
                        content_hash=row.sha256,
                        embedding=encoded["vector"],
                    )
                    await session.execute(
                        statement.on_conflict_do_update(
                            index_elements=["image_id", "model_name", "model_revision"],
                            set_={
                                "content_hash": row.sha256,
                                "embedding": encoded["vector"],
                            },
                        )
                    )
                    indexed += 1
                    print(f"Encoded {indexed}: {product.id}", flush=True)
                if page * 1000 >= total:
                    break
                page += 1
    await engine.dispose()
    result = {
        "indexed": indexed,
        "model": "OpenCLIP ViT-B/32",
        "revision": CLIP_REVISION,
        "dimension": 512,
        "device": "cpu",
        "gallery": "original CC0 SVG illustrations, rasterized offline",
        "preprocess": "openclip default 224 center crop, RGB, model mean/std; source SVG raster scale .8",
        "total_ms": round((time.perf_counter() - start) * 1000, 3),
        "first_model_load_ms": first["model_load_ms"] if first else None,
        "first_rss_mib": first["rss_mib"] if first else None,
    }
    Path("docs/evidence/image-index.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
