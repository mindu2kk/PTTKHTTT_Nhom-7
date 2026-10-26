"""Incrementally index approved catalog galleries with the existing local image encoder."""

import asyncio
import hashlib
import io
import json
import time
from pathlib import Path

from PIL import Image
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import CATALOG_MEDIA_ROOT, FIXTURE_ROOT
from app.domain.catalog import CatalogFilter
from app.domain.media import CleanImage
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.database import engine, session_factory
from app.infrastructure.media import CLIP_REVISION, HttpImageEncoder, sanitize
from app.infrastructure.models import ImageEmbedding, ProductImage
from app.infrastructure.product_image_url import fetch_image

MODEL_NAME = "OpenCLIP ViT-B/32"
PAGE_SIZE = 1000
MAX_IMAGE_BYTES = 5 * 1024 * 1024
IMAGE_FORMATS = {
    "PNG": ("image/png", "png"),
    "JPEG": ("image/jpeg", "jpg"),
    "WEBP": ("image/webp", "webp"),
}


async def load_public_images(session: AsyncSession, profile: str) -> list[ProductImage]:
    repository = SqlCatalogRepository(session, profile)
    product_ids: list[str] = []
    page = 1
    while True:
        products, total = await repository.list_products(
            CatalogFilter(page=page, page_size=PAGE_SIZE)
        )
        product_ids.extend(product.id for product in products)
        if page * PAGE_SIZE >= total:
            break
        page += 1

    allowed_licenses = ["demo", "approved"] if profile == "demo_seed" else ["approved"]
    query = (
        select(ProductImage)
        .where(
            ProductImage.product_id.in_(product_ids),
            ProductImage.license_status.in_(allowed_licenses),
        )
        .order_by(ProductImage.id)
    )
    return list(await session.scalars(query))


async def read_image_content(storage_key: str) -> bytes:
    if storage_key.startswith("https://"):
        return await fetch_image(storage_key)
    if storage_key.startswith("/media/catalog/"):
        directory = CATALOG_MEDIA_ROOT
        filename = storage_key.removeprefix("/media/catalog/")
    elif storage_key.startswith("/media/"):
        directory = FIXTURE_ROOT / "images"
        filename = storage_key.removeprefix("/media/")
    else:
        raise ValueError("Unsupported catalog image location")

    if (
        not filename
        or Path(filename).name != filename
        or "\\" in filename
        or filename in {".", ".."}
    ):
        raise ValueError("Image location must be a filename within the media directory")
    path = directory / filename
    if not path.resolve().is_relative_to(directory.resolve()):
        raise ValueError("Image location escapes the media directory")
    if path.stat().st_size > MAX_IMAGE_BYTES:
        raise ValueError("Image exceeds 5 MB")
    return path.read_bytes()


def prepare_image(content: bytes, storage_key: str) -> CleanImage:
    if storage_key.endswith(".svg"):
        # Only approved fixture SVGs use this optional offline rasterizer.
        import fitz

        with fitz.open(stream=content, filetype="svg") as document:
            content = (
                document[0].get_pixmap(matrix=fitz.Matrix(0.8, 0.8)).tobytes("png")
            )
    with Image.open(io.BytesIO(content)) as image:
        if image.format not in IMAGE_FORMATS:
            raise ValueError("Unsupported catalog image format")
        mime, extension = IMAGE_FORMATS[image.format]
    return sanitize(content, mime, f"catalog.{extension}")


async def index_catalog() -> dict[str, object]:
    started = time.perf_counter()
    settings = get_settings()
    encoder = HttpImageEncoder(settings.inference_url)
    encoded_count = skipped_count = 0
    first_call = None

    async with session_factory.begin() as session:
        images = await load_public_images(session, settings.data_profile)
        for image in images:
            existing = await session.get(
                ImageEmbedding, (image.id, MODEL_NAME, CLIP_REVISION)
            )
            if existing is not None and existing.content_hash == image.sha256:
                skipped_count += 1
                continue

            content = await read_image_content(image.storage_key)
            if hashlib.sha256(content).hexdigest() != image.sha256:
                raise ValueError(f"Approved image changed; review required: {image.id}")
            result = await encoder.encode(prepare_image(content, image.storage_key))
            if first_call is None:
                first_call = {
                    "model_load_ms": result.model_load_ms,
                    "inference_ms": result.inference_ms,
                }

            statement = insert(ImageEmbedding).values(
                image_id=image.id,
                model_name=MODEL_NAME,
                model_revision=result.revision,
                content_hash=image.sha256,
                embedding=list(result.vector),
            )
            await session.execute(
                statement.on_conflict_do_update(
                    index_elements=["image_id", "model_name", "model_revision"],
                    set_={
                        "content_hash": image.sha256,
                        "embedding": list(result.vector),
                    },
                )
            )
            encoded_count += 1
            print(
                f"Encoded {encoded_count}: {image.id}; skipped {skipped_count}",
                flush=True,
            )

    return {
        "encoded": encoded_count,
        "skipped_unchanged": skipped_count,
        "approved_images": len(images),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "revision": CLIP_REVISION,
        "first_call": first_call,
        "profile": settings.data_profile,
        "scope": "Current public catalog, primary and gallery, hash-checked; local inference",
    }


async def main() -> None:
    try:
        report = await index_catalog()
    finally:
        await engine.dispose()
    report_name = (
        "local-image-index.json"
        if report["encoded"]
        else "local-image-index-replay.json"
    )
    report_path = Path("artifacts") / report_name
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
