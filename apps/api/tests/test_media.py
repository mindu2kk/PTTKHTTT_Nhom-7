import io

import pytest
from PIL import Image
from sqlalchemy import update

from app.domain.media import MediaError
from app.infrastructure.database import engine, session_factory
from app.infrastructure.media import sanitize
from app.infrastructure.models import ImageEmbedding, ProductImage
from app.infrastructure.vectors import SqlImageVectorIndex


def png(width=100, height=100):
    image = Image.new("RGB", (width, height), "navy")
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "content,mime,name,status",
    [
        (b"not an image", "image/png", "x.png", 422),
        (b"<svg/>", "image/svg+xml", "x.svg", 422),
        (png(), "image/jpeg", "x.jpg", 422),
        (png(), "image/png", "x.heic", 422),
        (png(8, 8), "image/png", "tiny.png", 422),
        (b"x" * (5 * 1024 * 1024 + 1), "image/png", "large.png", 413),
    ],
    ids=["corrupt", "svg", "mime-mismatch", "heic", "tiny", "oversized"],
)
def test_actual_media_validation(content, mime, name, status):
    with pytest.raises(MediaError) as error:
        sanitize(content, mime, name)
    assert error.value.status == status


def test_exif_removed_and_large_pixels_rejected():
    image = Image.new("RGB", (100, 100), "navy")
    exif = Image.Exif()
    exif[270] = "private image metadata"
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    clean = sanitize(buffer.getvalue(), "image/jpeg", "photo.jpg")
    assert not Image.open(io.BytesIO(clean.content)).getexif()
    with pytest.raises(MediaError):
        sanitize(png(4000, 4000), "image/png", "bomb.png")


async def test_real_sql_exact_vector_prefilter_and_hash_version():
    async with session_factory() as session:
        for pid, vector in [
            ("sweater-01", [1.0] + [0.0] * 511),
            ("sweater-02", [0.0, 1.0] + [0.0] * 510),
        ]:
            image = await session.get(ProductImage, f"image-{pid}")
            session.add(
                ImageEmbedding(
                    image_id=image.id,
                    model_name="OpenCLIP ViT-B/32",
                    model_revision="test-revision",
                    content_hash=image.sha256,
                    embedding=vector,
                )
            )
        await session.flush()
        index = SqlImageVectorIndex(session)
        query = tuple([1.0] + [0.0] * 511)
        scores = await index.search(query, "test-revision", ("sweater-02",))
        assert list(scores) == ["sweater-02"] and scores["sweater-02"] == 0.5
        assert await index.search(query, "wrong-version", ("sweater-01",)) == {}
        await session.execute(
            update(ProductImage)
            .where(ProductImage.id == "image-sweater-02")
            .values(sha256="0" * 64)
        )
        assert await index.search(query, "test-revision", ("sweater-02",)) == {}
        await session.rollback()
    await engine.dispose()


@pytest.mark.parametrize("top_k", ["0", "-1", "101", "2.5", "abc"])
async def test_image_top_k_rejects_invalid_values_before_inference(client, monkeypatch, top_k):
    from unittest.mock import AsyncMock

    from app.core import dependencies

    encoder = AsyncMock()
    monkeypatch.setattr(dependencies, "image_encoder", encoder)
    response = await client.post(
        "/api/v1/search/image",
        files={"image": ("query.png", png(), "image/png")},
        data={"top_k": top_k},
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 422, response.text
    encoder.encode.assert_not_awaited()
