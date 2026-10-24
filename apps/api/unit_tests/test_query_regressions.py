"""Pure unit oracles: no DB, HTTP, model or fixture seeding."""

import unicodedata

import pytest

from app.application.query_parser import RuleQueryParser, amount
from app.domain.catalog import Category
from app.domain.search import SearchOptions

PARSER = RuleQueryParser(
    [
        Category("sneakers", None, "sneakers", "Giày thể thao", 1, 1),
        Category("headphones", None, "headphones", "Tai nghe", 1, 2),
        Category("furniture", None, "furniture", "Gia dụng", 1, 3),
    ]
)


@pytest.mark.parametrize(
    "phrase,expected",
    [
        ("năm trăm năm mươi nghìn", 550000),
        ("năm trăm linh năm nghìn", 505000),
        ("hai mươi lăm ngàn", 25000),
        ("một triệu hai trăm nghìn", 1200000),
        ("hai triệu năm trăm năm mươi nghìn đồng", 2550000),
        ("một tỷ", 1000000000),
        ("500.000 đồng", 500000),
        ("1,5 triệu", 1500000),
        ("1.5tr", 1500000),
        ("500k", 500000),
        ("hai ba nghìn", None),
        ("năm trăm linh", None),
        ("mèo", None),
    ],
)
def test_money_spoken_and_formatted_whole_vnd(phrase, expected):
    assert amount(phrase) == expected


@pytest.mark.parametrize(
    "phrase,key,value,operator",
    [
        ("tai nghe dưới năm trăm năm mươi nghìn", "price_max", 550000, "lt"),
        ("tai nghe không quá một triệu hai trăm nghìn", "price_max", 1200000, "lte"),
        ("giày thể thao từ hai trăm linh năm nghìn", "price_min", 205000, "gte"),
        ("tai nghe dưới 500.000 đồng", "price_max", 500000, "lt"),
    ],
)
def test_complete_money_phrase_is_not_silently_truncated(phrase, key, value, operator):
    c = next(c for c in PARSER.parse(phrase, "voice").hard_filters if c.key == key)
    assert (c.value, c.operator) == (value, operator)


@pytest.mark.parametrize(
    "phrase,forbidden",
    [
        ("tìm đèn bàn", "color"),
        ("tìm bàn bằng gỗ", "color"),
        ("đã có tai nghe", "material"),
        ("tôi đến mua tai nghe", "color"),
        ("cho tôi xem đồ gia dụng", "color"),
        ("giày cho bé", "color"),
        ("tai nghe không dây", "material"),
        ("bàn làm việc", "gender"),
    ],
)
def test_accent_homographs_do_not_become_unspoken_attributes(phrase, forbidden):
    assert not any(c.key == forbidden for c in PARSER.parse(phrase, "voice").hard_filters)


@pytest.mark.parametrize(
    "phrase,key,expected",
    [
        ("tai nghe màu đen", "color", "đen"),
        ("tai nghe mau den", "color", "đen"),
        ("giày màu đỏ", "color", "đỏ"),
        ("giay mau do", "color", "đỏ"),
        ("bàn màu vàng", "color", "vàng"),
        ("giày bằng da", "material", "da"),
    ],
)
def test_actual_explicit_attributes_still_work(phrase, key, expected):
    assert next(c.value for c in PARSER.parse(phrase).hard_filters if c.key == key) == expected


def test_nfc_voice_and_ui_filters_preserve_user_intent():
    raw = unicodedata.normalize("NFD", "tai nghe màu đen dưới năm trăm nghìn")
    rep = PARSER.parse(
        raw, "voice", SearchOptions(category="furniture", color="đỏ", price_max=900000)
    )
    assert rep.raw_text == unicodedata.normalize("NFC", raw)
    values = {c.key: c for c in rep.hard_filters}
    assert [(values[k].value, values[k].origin) for k in ("category", "color", "price_max")] == [
        ("furniture", "ui_selected"),
        ("đỏ", "ui_selected"),
        (900000, "ui_selected"),
    ]


def test_unknown_phrase_does_not_invent_category_or_budget():
    rep = PARSER.parse("tôi muốn mua vật thể sao hỏa", "voice")
    assert not rep.hard_filters


@pytest.mark.parametrize("phrase", ["năm đôi giày", "năm chiếc tai nghe", "nam doi giay"])
def test_spoken_quantity_is_not_male_gender(phrase):
    assert not any(c.key == "gender" for c in PARSER.parse(phrase, "voice").hard_filters)


@pytest.mark.parametrize(
    "phrase",
    [
        "tai nghe dưới hai ba nghìn",
        "tai nghe dưới năm trăm linh",
        "tai nghe dưới 999999999999999k",
    ],
)
def test_invalid_or_oversized_spoken_budget_is_not_partially_accepted(phrase):
    assert not any(c.key.startswith("price") for c in PARSER.parse(phrase, "voice").hard_filters)


@pytest.mark.parametrize(
    "phrase,key,value,op",
    [
        ("tai nghe không dưới năm trăm nghìn", "price_min", 500000, "gte"),
        ("tai nghe ít nhất 200k", "price_min", 200000, "gte"),
        ("tai nghe không trên 500k", "price_max", 500000, "lte"),
    ],
)
def test_negated_price_direction_is_not_inverted(phrase, key, value, op):
    constraints = {c.key: c for c in PARSER.parse(phrase).hard_filters}
    assert (constraints[key].value, constraints[key].operator) == (value, op)


@pytest.mark.parametrize(
    "phrase", ["tai nghe từ 200k đến 500k", "tai nghe từ hai trăm nghìn tới năm trăm nghìn"]
)
def test_spoken_price_range_keeps_both_boundaries(phrase):
    constraints = {c.key: c for c in PARSER.parse(phrase).hard_filters}
    assert (constraints["price_min"].value, constraints["price_min"].operator) == (200000, "gte")
    assert (constraints["price_max"].value, constraints["price_max"].operator) == (500000, "lte")
