"""Service contract checks with test-only recognizer/catalog ports; no DB or ASR."""

import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from app.application.speech import SpeechService
from app.domain.catalog import CatalogFilter, CatalogRepository, Product
from app.domain.media import MediaError, SpeechRecognizer, Transcript


def transcript(text="tôi muốn mua máy dặt dưới 500k"):
    return Transcript(text, "vi", 2.0, "test-only-recognizer", "test-revision", 5, 10, ())


def simulated_product(**changes):
    # Domain Product is the public repository result; it has no publication flag.
    product = Product(
        id="original-simulated-product",
        slug="original-simulated-product",
        name_vi="Máy giặt — DEMO123",
        description_vi="Fixture tự tạo cho unit test.",
        category_id="simulated-category",
        category_name="Máy giặt",
        price_vnd=500000,
        available_quantity=1,
        image_url="approved/simulated.jpg",
        image_alt="Fixture ảnh",
        color="trắng",
        material="nhựa",
        size="M",
        gender=None,
        verification_status="verified",
        price_kind="demo",
        source_id="original-unit-fixture",
        rights_status="demo",
        data_profile="demo_seed",
    )
    return replace(product, **changes)


def ports(result=None, products=None):
    recognizer = AsyncMock(spec=SpeechRecognizer)
    recognizer.transcribe.return_value = result or transcript()
    catalog = AsyncMock(spec=CatalogRepository)
    catalog.list_products.return_value = (products or [simulated_product()], 1)
    return recognizer, catalog


async def test_catalog_is_not_accessed_until_recognizer_finishes():
    recognizer, catalog = ports()
    started, finish_asr = asyncio.Event(), asyncio.Event()
    calls = []

    async def recognize(*_args):
        calls.append("recognizer-start")
        started.set()
        await finish_asr.wait()
        calls.append("recognizer-finished")
        return transcript()

    async def lookup(filters):
        assert finish_asr.is_set()
        assert calls == ["recognizer-start", "recognizer-finished"]
        assert filters == CatalogFilter(page_size=1000)
        calls.append("public-catalog")
        return [simulated_product()], 1

    recognizer.transcribe.side_effect = recognize
    catalog.list_products.side_effect = lookup
    task = asyncio.create_task(
        SpeechService(recognizer, catalog).transcribe(b"unit", "audio/wav", "u.wav")
    )
    try:
        await asyncio.wait_for(started.wait(), timeout=1)
        catalog.list_products.assert_not_awaited()
        finish_asr.set()
        result = await asyncio.wait_for(task, timeout=1)
    finally:
        if not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
    assert calls == ["recognizer-start", "recognizer-finished", "public-catalog"]
    assert result.suggestions == ("tôi muốn mua máy giặt dưới 500k",)


@pytest.mark.parametrize("raw", ["", " \n\t", "x" * 301])
async def test_invalid_asr_never_queries_catalog(raw):
    recognizer, catalog = ports(transcript(raw))
    with pytest.raises(MediaError) as caught:
        await SpeechService(recognizer, catalog).transcribe(b"unit", "audio/wav", "u.wav")
    assert caught.value.status == 422
    catalog.list_products.assert_not_awaited()


async def test_failed_asr_never_queries_catalog_or_fabricates_transcript():
    recognizer, catalog = ports()
    recognizer.transcribe.side_effect = MediaError(503, "Chưa nhận được âm thanh.")
    with pytest.raises(MediaError) as caught:
        await SpeechService(recognizer, catalog).transcribe(b"unit", "audio/wav", "u.wav")
    assert caught.value.status == 503
    catalog.list_products.assert_not_awaited()


async def test_failed_catalog_preserves_recognizer_text_metadata_and_warnings():
    source = replace(transcript(), warnings=("Hãy kiểm tra câu đã nhận.",))
    recognizer, catalog = ports(source)
    catalog.list_products.side_effect = RuntimeError("private-database-details-must-not-leak")
    result = await SpeechService(recognizer, catalog).transcribe(b"unit", "audio/wav", "u.wav")
    assert result.text == source.text
    assert result.suggestions == ()
    assert result.warnings[0] == source.warnings[0]
    assert len(result.warnings) == 2
    assert "tạm chưa sẵn sàng" in result.warnings[-1]
    assert "private" not in " ".join(result.warnings)
    assert replace(result, warnings=(), suggestions=()) == replace(source, warnings=())


async def test_public_catalog_produces_opt_in_generic_alternative_without_replacing_asr():
    source = transcript("  tôi muốn mua máy dặt màu đen dưới năm trăm nghìn  ")
    recognizer, catalog = ports(source)
    result = await SpeechService(recognizer, catalog).transcribe(b"unit", "audio/wav", "u.wav")
    assert result.text == source.text.strip()
    assert result.suggestions == ("tôi muốn mua máy giặt màu đen dưới năm trăm nghìn",)
    recognizer.transcribe.assert_awaited_once_with(b"unit", "audio/wav", "u.wav")
    catalog.list_products.assert_awaited_once_with(CatalogFilter(page_size=1000))
    catalog.get_product.assert_not_awaited()
    catalog.categories.assert_not_awaited()


@pytest.mark.parametrize(
    "changes",
    [
        {"rights_status": "unapproved"},
        {"rights_status": "quarantined"},
        {"verification_status": "pending"},
        {"image_url": ""},
        {"source_id": ""},
    ],
)
async def test_unapproved_or_incomplete_catalog_product_never_supplies_suggestion(changes):
    recognizer, catalog = ports(products=[simulated_product(**changes)])
    result = await SpeechService(recognizer, catalog).transcribe(b"unit", "audio/wav", "u.wav")
    assert result.text == transcript().text
    assert result.suggestions == ()
    assert result.warnings == ()


async def test_catalog_cancellation_is_not_swallowed_as_optional_lookup_failure():
    recognizer, catalog = ports()
    catalog.list_products.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await SpeechService(recognizer, catalog).transcribe(b"unit", "audio/wav", "u.wav")


async def test_optional_catalog_default_preserves_legacy_suggestions():
    recognizer, _catalog = ports(transcript("mua tài nghe"))
    result = await SpeechService(recognizer).transcribe(b"unit", "audio/wav", "u.wav")
    assert result.text == "mua tài nghe"
    assert result.suggestions == ("mua tai nghe",)
