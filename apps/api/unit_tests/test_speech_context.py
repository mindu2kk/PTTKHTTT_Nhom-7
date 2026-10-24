from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from app.application.speech import SpeechService
from app.application.speech_context import (
    MAX_SUGGESTIONS,
    MAX_VOCABULARY,
    SpeechVocabularyEntry,
    product_alternatives,
    public_product_vocabulary,
)
from app.domain.catalog import Product
from app.domain.media import MediaError, Transcript


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("tôi muốn mua tài nghe dưới 500k", "tôi muốn mua tai nghe dưới 500k"),
        ("tìm dày thể thao màu đen", "tìm giày thể thao màu đen"),
        ("tìm bàng làm việc", "tìm bàn làm việc"),
        ("mua áo khoát dưới năm trăm nghìn", "mua áo khoác dưới năm trăm nghìn"),
    ],
)
def test_near_sound_product_phrase_offers_opt_in_alternative(raw, expected):
    assert expected in product_alternatives(raw)


@pytest.mark.parametrize(
    "text",
    [
        "tôi muốn mua áo lông",
        "áo len",
        "tai nghe",
        "bàn",
        "ban",
        "dày",
        "áo",
        "giày màu đen dưới năm trăm nghìn",
        "hôm nay trời đẹp",
        "kiểm tra đơn hàng 123456 tài nghe",
    ],
)
def test_valid_or_ambiguous_speech_is_not_forced_into_another_product(text):
    assert not product_alternatives(text)


async def test_speech_service_preserves_recognizer_text_and_exposes_only_suggestions():
    recognizer = AsyncMock()
    recognizer.transcribe.return_value = Transcript(
        "tôi muốn mua tài nghe dưới 500k",
        "vi",
        2.0,
        "test-only",
        "revision",
        0,
        0,
        ("Chưa chắc chắn.",),
    )
    result = await SpeechService(recognizer).transcribe(b"test", "audio/wav", "x.wav")
    assert result.text == "tôi muốn mua tài nghe dưới 500k"
    assert result.suggestions == ("tôi muốn mua tai nghe dưới 500k",)
    assert result.warnings == ("Chưa chắc chắn.",)


@pytest.mark.parametrize("text", ["", " \n\t", "x" * 301])
async def test_unusable_speech_never_becomes_fabricated_product_query(text):
    recognizer = AsyncMock()
    recognizer.transcribe.return_value = Transcript(text, "vi", 1, "test", "rev", 0, 0, ())
    with pytest.raises(MediaError) as caught:
        await SpeechService(recognizer).transcribe(b"test", "audio/wav", "x.wav")
    assert caught.value.status == 422


async def test_recognizer_failure_remains_failure():
    recognizer = AsyncMock()
    recognizer.transcribe.side_effect = MediaError(503, "Chưa nhận được âm thanh.")
    with pytest.raises(MediaError) as caught:
        await SpeechService(recognizer).transcribe(b"test", "audio/wav", "x.wav")
    assert caught.value.status == 503


# Catalog examples below are simulated vocabulary, not claims about live inventory.


def vocabulary(*phrases):
    return tuple(
        SpeechVocabularyEntry(phrase, "unit-original", "published", "verified", "demo", "demo")
        for phrase in phrases
    )


@pytest.mark.parametrize(
    "raw,phrase,expected",
    [
        ("tìm quạc trần", "quạt trần", "tìm quạt trần"),
        ("mua đèn bàng", "đèn bàn", "mua đèn bàn"),
        ("tôi tìm máy say", "máy xay", "tôi tìm máy xay"),
        ("chọn loa blutooth", "loa bluetooth", "chọn loa bluetooth"),
        (
            "tôi muốn mua máy sát màu đen dưới 500.000 đồng",
            "máy sắt",
            "tôi muốn mua máy sắt màu đen dưới 500.000 đồng",
        ),
    ],
)
def test_public_vocabulary_adds_bounded_near_syllable_proposals(raw, phrase, expected):
    assert product_alternatives(raw) == ()
    assert expected in product_alternatives(raw, vocabulary(phrase))
    assert raw != expected  # The helper proposes a second value, never overwrites raw.


@pytest.mark.parametrize(
    "text,phrases",
    [
        ("hôm nay quạc trần đẹp", ("quạt trần",)),
        ("tôi mua áo lông", ("áo len",)),
        ("tôi mua áo len", ("áo lông",)),
        ("mua máy say", ("máy say", "máy xay", "máy sấy")),
        ("tìm đen bàn", ("đèn bàn",)),
        ("tìm máy năm", ("máy nam",)),
        ("tìm máy năm trăm nghìn", ("máy nam",)),
        ("chọn máy lọc khôn khí", ("máy lọc không khí",)),
        ("mua máy 123", ("máy xay",)),
        ("mua máy SAY", ("máy xay",)),
        ("mua máy-say", ("máy xay",)),
        ("mua máy/say", ("máy xay",)),
        ("mua AC-quạc trần", ("quạt trần",)),
        ("mua đèn bàng.ABC", ("đèn bàn",)),
        ("tìm xay", ("xay",)),
        ("mua quạt trần", ("quạt trần", "quạt chân")),
        ("tôi muốn hủy đơn hàng và mua tài nghe", ("tai nghe",)),
        ("mua quạc trần mã HM0123456789abcd", ("quạt trần",)),
        ("tôi đang nghe tài nghe kể chuyện", ("tai nghe",)),
    ],
)
def test_context_protects_real_names_attributes_codes_and_nonshopping_speech(text, phrases):
    assert product_alternatives(text, vocabulary(*phrases)) == ()


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_id", ""),
        ("source_id", " "),
        ("publication_status", "draft"),
        ("publication_status", ""),
        ("verification_status", "pending"),
        ("rights_status", "quarantined"),
        ("rights_status", "unknown"),
        ("image_rights_status", "pending"),
        ("image_rights_status", "approved"),
    ],
)
def test_vocabulary_provenance_and_image_gate_is_fail_closed(field, value):
    entry = replace(vocabulary("quạt trần")[0], **{field: value})
    assert product_alternatives("mua quạc trần", (entry,)) == ()


def test_vocabulary_entry_default_has_no_implicit_approval():
    assert product_alternatives("mua quạc trần", (SpeechVocabularyEntry("quạt trần"),)) == ()


def test_alternatives_keep_ambiguous_candidates_visible_and_deterministic():
    phrases = vocabulary("máy sấy", "máy xay")
    expected = ("mua máy sấy", "mua máy xay")
    assert product_alternatives("mua máy say", phrases) == expected
    assert product_alternatives("mua máy say", reversed(phrases)) == expected


def test_unchanged_spans_are_byte_identical_including_budget_color_and_code():
    raw = "Mua quạc trần, màu ĐỎ; giá từ năm trăm nghìn đến 1.200.000đ, mã AC-42."
    assert product_alternatives(raw, vocabulary("quạt trần")) == (raw.replace("quạc", "quạt"),)


def test_long_phrase_only_changes_one_syllable_and_preserves_extra_description():
    raw = "tìm máy xay sinh tố cầm tay loại nhỏ dưới 300k"
    assert product_alternatives(raw, vocabulary("máy xay sinh tô cầm tay")) == (
        raw.replace("tố", "tô"),
    )
    assert product_alternatives("mua mây say", vocabulary("máy xay")) == ()


def test_all_suggestions_are_capped_and_deduplicated():
    raw = "mua tài nghe dày thể thao bàng làm việc áo khoát"
    result = product_alternatives(raw, vocabulary("tai nghe"))
    assert len(result) == len(set(result)) == MAX_SUGGESTIONS
    # Each proposal represents one local correction, not a speculative chain.
    assert all(
        sum(a != b for a, b in zip(raw.split(), item.split(), strict=True)) == 1 for item in result
    )


@pytest.mark.parametrize("phrase", ["quạt", "quạt 123", "quạt/trần", "x " * 8, "q" * 81])
def test_unbounded_or_code_bearing_vocabulary_is_ignored(phrase):
    assert product_alternatives("mua quạc trần", vocabulary(phrase)) == ()


def test_context_input_and_iterable_work_are_bounded():
    assert product_alternatives("x" * 301, vocabulary("quạt trần")) == ()
    visited = []

    def entries():
        for i in range(5000):
            visited.append(i)
            yield SpeechVocabularyEntry("quạt trần")  # Unapproved; still bounded.

    assert product_alternatives("mua quạc trần", entries()) == ()
    assert len(visited) == 2048


def public_product(**changes):
    base = Product(
        id="simulated-1",
        slug="simulated-1",
        name_vi="Quạt trần — ABC123",
        description_vi="Không lấy từ vựng từ mô tả chưa cấu trúc.",
        category_id="c",
        category_name="Quạt trần",
        price_vnd=123000,
        available_quantity=1,
        image_url="approved/local.jpg",
        image_alt="Ảnh mô phỏng",
        color="trắng",
        material="nhựa",
        size="M",
        gender=None,
        verification_status="verified",
        price_kind="demo",
        source_id="unit-original",
        rights_status="demo",
        data_profile="demo_seed",
    )
    return replace(base, **changes)


def test_public_catalog_adapter_extracts_reviewed_category_and_code_free_title():
    entries = public_product_vocabulary(
        [
            public_product(),
            public_product(name_vi="Máy xay — XYZ999"),
            public_product(),
        ]
    )
    assert {entry.phrase for entry in entries} == {"quạt trần", "máy xay"}
    assert product_alternatives("mua quạc trần", entries) == ("mua quạt trần",)
    assert all(entry.source_id == "unit-original" for entry in entries)


@pytest.mark.parametrize(
    "changes",
    [
        {"verification_status": "pending"},
        {"rights_status": "quarantined"},
        {"image_url": ""},
        {"source_id": ""},
    ],
)
def test_public_catalog_adapter_refuses_unsafe_incomplete_products(changes):
    assert public_product_vocabulary([public_product(**changes)]) == ()


def test_public_catalog_adapter_accepts_approved_rights_and_caps_distinct_phrases():
    entries = public_product_vocabulary(
        public_product(
            category_name=f"quạt {chr(97 + i // 26)}{chr(97 + i % 26)}",
            name_vi="Mã 123",
            rights_status="approved",
        )
        for i in range(600)
    )
    assert len(entries) == MAX_VOCABULARY
    assert all(entry.rights_status == entry.image_rights_status == "approved" for entry in entries)


def test_public_catalog_adapter_does_not_learn_proper_name_title_suffixes():
    entries = public_product_vocabulary(
        [
            public_product(name_vi="Bàn Rivet — CT355C", category_name="Bàn Phụ"),
        ]
    )
    assert tuple(entry.phrase for entry in entries) == ("bàn phụ",)
    assert product_alternatives("mua bàn rivot", entries) == ()


def test_confirmation_does_not_chain_legacy_rules_or_change_original_case_spans():
    raw = "MUA tài nghe, dày thể thao dưới 500k"
    choices = product_alternatives(raw)
    assert len(choices) == 2
    assert all(item.startswith("MUA ") and item.endswith(" dưới 500k") for item in choices)
    assert "MUA tai nghe, giày thể thao dưới 500k" not in choices


@pytest.mark.parametrize(
    "raw,phrase,expected",
    [
        ("mua máy dặt", "máy giặt", "mua máy giặt"),
        ("tìm quạt chần", "quạt trần", "tìm quạt trần"),
        ("chọn gươn trang điểm", "gương trang điểm", "chọn gương trang điểm"),
        ("mua máy lộc nước", "máy lọc nước", "mua máy lọc nước"),
    ],
)
def test_reviewed_syllable_families_produce_confirmable_product_candidates(raw, phrase, expected):
    assert product_alternatives(raw, vocabulary(phrase)) == (expected,)


def test_phonetic_families_do_not_chain_two_changes_in_one_syllable():
    assert product_alternatives("mua quạt chầng", vocabulary("quạt trần")) == ()


def test_long_query_alternative_must_fit_search_contract():
    suffix = "mua dày thể thao"
    raw = "x" * (300 - len(suffix) - 1) + " " + suffix
    assert len(raw) == 300
    assert not product_alternatives(raw)
