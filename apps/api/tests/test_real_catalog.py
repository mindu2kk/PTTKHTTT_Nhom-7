"""M8 gates use original synthetic test-only metadata/photos in the separate test DB."""

import copy
import hashlib
import io

import pytest
from PIL import Image
from sqlalchemy import func, select, update

from app.domain.catalog import CatalogFilter
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.database import engine, session_factory
from app.infrastructure.media import CLIP_REVISION
from app.infrastructure.models import (
    CategoryRow,
    DataSource,
    ImageEmbedding,
    ProductImage,
    SellerOffer,
    SourceProduct,
)
from app.infrastructure.real_catalog import (
    REVISION,
    SOURCE,
    ensure_reviewed,
    load_catalog,
    validate_manifest,
)
from app.infrastructure.vectors import SqlImageVectorIndex


@pytest.fixture
def sample(tmp_path):
    external = "unit.invalid:TEST-M8-1"
    pid = "abo-" + hashlib.sha256(external.encode()).hexdigest()[:20]
    images = []
    for n in range(2):
        output = io.BytesIO()
        Image.new("RGB", (100, 100), (n * 50, 90, 20)).save(output, format="WEBP")
        raw = output.getvalue()
        (tmp_path / f"{pid}-{n}.webp").write_bytes(raw)
        images.append(
            {
                "url": f"/media/catalog/{pid}-{n}.webp",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "source_image_id": f"TEST-IMAGE-{n}",
                "width": 100,
                "height": 100,
                "primary": n == 0,
            }
        )
    manifest = {
        "source": SOURCE,
        "revision": REVISION,
        "license": "CC-BY-4.0",
        "errors": [],
        "records": [
            {
                "id": pid,
                "external_id": external,
                "raw": {
                    "item_id": "TEST-M8-1",
                    "domain_name": "unit.invalid",
                    "main_image_id": "TEST-IMAGE-0",
                    "other_image_id": ["TEST-IMAGE-1"],
                    "product_type": [{"value": "HEADPHONES"}],
                },
                "group": "dien-tu",
                "category_id": "abo-tai-nghe",
                "category_name": "Tai nghe",
                "name_vi": "Tai nghe dữ liệu unit test",
                "original_name": "Original test fixture",
                "description_vi": "Chỉ dùng trong database kiểm thử",
                "brand": "Unit Test",
                "gender": None,
                "color": "đen",
                "material": "",
                "price_vnd": 390000,
                "demo_capacity": 5,
                "images": images,
            }
        ],
    }
    return manifest, tmp_path


@pytest.mark.parametrize(
    "failure",
    [
        "license",
        "source",
        "revision",
        "missing_id",
        "duplicate",
        "wrong_photo",
        "wrong_secondary",
        "unsafe_path",
        "bad_category",
        "wrong_category",
        "swatch",
        "placeholder",
        "missing_image",
        "corrupt_image",
    ],
)
def test_import_validation_negative(sample, failure):
    original, directory = sample
    manifest = copy.deepcopy(original)
    record = manifest["records"][0]
    if failure == "license":
        manifest["license"] = "unknown"
    elif failure == "source":
        manifest["source"] = "unreviewed"
    elif failure == "revision":
        manifest["revision"] = "new-version"
    elif failure == "missing_id":
        record["raw"].pop("item_id")
    elif failure == "duplicate":
        manifest["records"].append(copy.deepcopy(record))
    elif failure == "wrong_photo":
        record["images"][0]["source_image_id"] = "UNRELATED"
    elif failure == "wrong_secondary":
        record["images"][1]["source_image_id"] = "UNRELATED"
    elif failure == "unsafe_path":
        record["images"][0]["url"] = "/media/catalog/../../.env"
    elif failure == "bad_category":
        record["group"] = "unknown"
    elif failure == "wrong_category":
        record["category_id"] = "abo-sofa"
    elif failure == "swatch":
        record["raw"]["item_name"] = [{"language_tag": "en_US", "value": "Fabric Swatch"}]
    elif failure == "placeholder":
        record["raw"]["main_image_id"] = "61kVdTXTJ4L"
    elif failure == "missing_image":
        (directory / f"{record['id']}-0.webp").unlink()
    elif failure == "corrupt_image":
        (directory / f"{record['id']}-0.webp").write_bytes(b"not an image")
    with pytest.raises((ValueError, OSError)):
        validate_manifest(manifest, directory)


def test_new_source_record_needs_explicit_visual_review(sample):
    with pytest.raises(ValueError, match="before publication"):
        ensure_reviewed(sample[0])


async def test_real_import_idempotency_mapping_and_rights(sample):
    manifest, directory = sample
    record = manifest["records"][0]
    try:
        async with session_factory() as session:
            try:
                first = await load_catalog(session, manifest, directory)
                second = await load_catalog(session, manifest, directory)
                assert first["created"] == 1 and second["created"] == 0 and second["reused"] == 1
                await session.flush()
                # This historical M8 fixture is explicitly enabled only in this test.
                await session.execute(
                    update(CategoryRow)
                    .where(CategoryRow.id == record["category_id"])
                    .values(is_active=True)
                )
                repository = SqlCatalogRepository(session, "real_demo")
                product = await repository.get_product(record["id"])
                assert (
                    product and product.price_kind == "demo" and product.data_profile == "real_demo"
                )
                assert product.rights_status == "approved" and len(product.images) == 2
                assert product.image_url == record["images"][0]["url"]
                assert product.brand == "Unit Test"
                products, total = await repository.list_products(
                    CatalogFilter(category="dien-tu", available=True)
                )
                assert total == 1 and products[0].id == record["id"]
                assert record["category_id"] in {c.id for c in await repository.categories()}
                # Unchanged source import must preserve operator price edits.
                await session.execute(
                    update(SellerOffer)
                    .where(SellerOffer.product_id == record["id"])
                    .values(price_vnd=123000)
                )
                await load_catalog(session, manifest, directory)
                assert (await repository.get_product(record["id"])).price_vnd == 123000
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(SourceProduct)
                        .where(SourceProduct.source_id == SOURCE)
                    )
                    == 1
                )
                assert (
                    await session.scalar(
                        select(func.count())
                        .select_from(ProductImage)
                        .where(ProductImage.product_id == record["id"])
                    )
                    == 2
                )
                assert (
                    await SqlCatalogRepository(session, "demo_seed").get_product(record["id"])
                    is None
                )
                await session.execute(
                    update(DataSource)
                    .where(DataSource.id == SOURCE)
                    .values(rights_status="restricted")
                )
                assert await repository.get_product(record["id"]) is None
                with pytest.raises(ValueError, match="revoked"):
                    await load_catalog(session, manifest, directory)
            finally:
                await session.rollback()
    finally:
        await engine.dispose()


async def test_real_manifest_change_requires_reconciliation(sample):
    manifest, directory = sample
    try:
        async with session_factory() as session:
            try:
                await load_catalog(session, manifest, directory)
                manifest["records"][0]["raw"]["new_field"] = "changed"
                with pytest.raises(ValueError, match="revision changed"):
                    await load_catalog(session, manifest, directory)
            finally:
                await session.rollback()
    finally:
        await engine.dispose()


async def test_gallery_vectors_aggregate_and_reject_revoked_photo(sample):
    manifest, directory = sample
    pid = manifest["records"][0]["id"]
    try:
        async with session_factory() as session:
            try:
                await load_catalog(session, manifest, directory)
                for n in range(2):
                    photo = manifest["records"][0]["images"][n]
                    session.add(
                        ImageEmbedding(
                            image_id=f"image-{pid}-{n}",
                            model_name="OpenCLIP ViT-B/32",
                            model_revision=CLIP_REVISION,
                            content_hash=photo["sha256"],
                            embedding=[1.0, 0.0] + [0.0] * 510 if n else [0.0, 1.0] + [0.0] * 510,
                        )
                    )
                await session.flush()
                index = SqlImageVectorIndex(session)
                query = (1.0, 0.0) + (0.0,) * 510
                result = await index.search(query, CLIP_REVISION, (pid,))
                assert list(result) == [pid] and result[pid] == 1.0
                await session.execute(
                    update(ProductImage)
                    .where(ProductImage.id == f"image-{pid}-1")
                    .values(license_status="restricted")
                )
                result = await index.search(query, CLIP_REVISION, (pid,))
                assert result[pid] == 0.5
                assert await index.search(query, "incompatible", (pid,)) == {}
            finally:
                await session.rollback()
    finally:
        await engine.dispose()


@pytest.mark.parametrize("action", ["create", "publish", "update", "archive", "import"])
async def test_real_catalog_management_remains_read_only_for_sellers(action):
    from app.domain.commerce import Actor, BusinessError
    from app.infrastructure.commerce import SqlCommerceStore

    store = SqlCommerceStore(session_factory, "real_demo")
    actor = Actor("fixture-customer", "fixture-customer@example.invalid", ("seller",), False)
    with pytest.raises(BusinessError) as error:
        await store.manage(actor, action, {"id": "sweater-01"})
    assert error.value.status == 409


async def test_management_profile_isolation():
    from app.domain.commerce import Actor
    from app.infrastructure.commerce import SqlCommerceStore

    actor = Actor("fixture-customer", "fixture-customer@example.invalid", ("admin",), False)
    try:
        result = await SqlCommerceStore(session_factory, "real_demo").manage(actor, "list", {})
        assert result["read_only"] is False and result["items"] == []
        photos = await SqlCommerceStore(session_factory, "real_demo").manage(actor, "images", {})
        assert photos["items"] == []
    finally:
        await engine.dispose()
