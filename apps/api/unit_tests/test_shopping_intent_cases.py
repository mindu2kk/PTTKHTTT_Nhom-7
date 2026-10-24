"""Conversational shopping oracles, independent of ASR and database state.

The representative category names/IDs match the reviewed M8 mapping. Product
fixtures below are original simulated records, not imported catalog assertions.
Known ranking gaps remain strict xfails until the root ranking fix lands.
Passing these text oracles does not establish the user's 70% spoken-search goal.
"""

from dataclasses import replace

import pytest

from app.application.query_parser import RuleQueryParser, amount, shopping_clarification
from app.application.search import RankingService
from app.domain.catalog import Category, Product
from app.domain.search import SearchOptions

PARSER = RuleQueryParser(
    [
        Category("abo-tai-nghe", None, "abo-tai-nghe", "Tai nghe", 2, 1),
        Category("abo-loa", None, "abo-loa", "Loa", 2, 2),
        Category("abo-den-ban", None, "abo-den-ban", "Đèn bàn", 2, 3),
        Category("abo-ban", None, "abo-ban", "Bàn", 2, 4),
        Category("abo-ban-phim", None, "abo-ban-phim", "Bàn phím", 2, 5),
        Category("abo-giay-nam", None, "abo-giay-nam", "Giày nam", 2, 6),
        Category("abo-giay-nu", None, "abo-giay-nu", "Giày nữ", 2, 7),
        Category("abo-chao", None, "abo-chao", "Chảo", 2, 8),
        Category("abo-goi", None, "abo-goi", "Gối", 2, 9),
        Category("abo-coc", None, "abo-coc", "Cốc", 2, 10),
    ]
)
KNOWN_RANK = pytest.mark.xfail(
    strict=True, reason="Audit: phrase intent is lost to category score floor/token stop list"
)


def constraints(text, options=None):
    return {c.key: c for c in PARSER.parse(text, "voice", options).hard_filters}


@pytest.mark.parametrize(
    "text,key,value,op",
    [
        ("cho mình xem loa giá dưới một triệu nhé", "price_max", 1000000, "lt"),
        ("mình muốn tai nghe màu đen không quá năm trăm nghìn", "color", "đen", "eq"),
        ("mình muốn tai nghe màu đen không quá năm trăm nghìn", "price_max", 500000, "lte"),
        ("cho tôi xem đèn bàn màu trắng", "category", "abo-den-ban", "eq"),
        ("tôi cần giày nữ dưới hai triệu", "gender", "nữ", "eq"),
        ("loa từ năm trăm nghìn đến bảy trăm nghìn", "price_min", 500000, "gte"),
        ("loa từ năm trăm nghìn đến bảy trăm nghìn", "price_max", 700000, "lte"),
        ("tai nghe không dưới năm trăm nghìn", "price_min", 500000, "gte"),
    ],
)
def test_supported_conversational_requests_keep_exact_constraints(text, key, value, op):
    c = constraints(text)[key]
    assert (c.value, c.operator) == (value, op)


@pytest.mark.parametrize(
    "text,key,forbidden",
    [
        ("tôi cần tai nghe không lấy màu trắng", "color", "trắng"),
        ("tôi muốn giày không phải màu trắng mà màu đen", "color", "trắng"),
        ("không mua giày da tôi cần giày vải", "material", "da"),
        ("tôi cần giày nữ không phải giày nam", "gender", "nam"),
        ("tôi muốn tai nghe không phải của samsung", "brand", "samsung"),
    ],
)
def test_negated_attribute_must_never_become_positive_equality(text, key, forbidden):
    c = constraints(text).get(key)
    assert c is None or c.value != forbidden


@pytest.mark.parametrize(
    "text,expected",
    [
        ("không phải tai nghe tôi cần loa", "abo-loa"),
        ("cho tôi xem đèn bàn tôi không mua tai nghe", "abo-den-ban"),
        ("không tìm bàn phím tôi muốn một cái bàn", "abo-ban"),
    ],
)
def test_positive_category_beats_a_longer_negated_category(text, expected):
    assert constraints(text)["category"].value == expected


@pytest.mark.parametrize(
    "text,key,value,op",
    [
        ("tai nghe ngân sách tối đa là năm trăm nghìn", "price_max", 500000, "lte"),
        ("loa rẻ hơn năm trăm nghìn", "price_max", 500000, "lt"),
        ("loa ít hơn năm trăm nghìn", "price_max", 500000, "lt"),
        ("loa năm trăm nghìn trở xuống", "price_max", 500000, "lte"),
        ("loa năm trăm nghìn trở lên", "price_min", 500000, "gte"),
    ],
)
def test_conversational_budget_operators_cannot_silently_disappear(text, key, value, op):
    c = constraints(text)[key]
    assert (c.value, c.operator) == (value, op)


def test_spoken_half_million_must_not_be_truncated_to_a_whole_million():
    c = constraints("loa dưới một triệu rưỡi")["price_max"]
    assert (c.value, c.operator) == (1500000, "lt")


def test_shared_unit_range_must_not_create_a_five_hundred_vnd_lower_bound():
    values = constraints("loa từ năm trăm đến bảy trăm nghìn")
    assert (values["price_min"].value, values["price_max"].value) == (500000, 700000)


def test_ui_constraints_remain_authoritative_over_spoken_corrections():
    values = constraints(
        "không phải tai nghe tôi cần loa màu đen dưới năm trăm nghìn",
        SearchOptions(category="abo-den-ban", color="trắng", price_max=900000),
    )
    assert [(values[k].value, values[k].origin) for k in ("category", "color", "price_max")] == [
        ("abo-den-ban", "ui_selected"),
        ("trắng", "ui_selected"),
        (900000, "ui_selected"),
    ]


@pytest.mark.parametrize("text", ["tai nghe không dây", "loa không dây", "bàn phím không dây"])
def test_fixed_wireless_phrase_must_not_negate_its_product_category(text):
    assert constraints(text)["category"].origin == "explicit_text"


def simulated_product(identifier, name, category="Bàn phím", category_id="abo-ban-phim"):
    return Product(
        identifier,
        identifier,
        name,
        "Fixture tự tạo cho kiểm thử ranking.",
        category_id,
        category,
        300000,
        1,
        "/simulated.jpg",
        "Ảnh fixture",
        "đen",
        "nhựa",
        "M",
        None,
        "verified",
        "demo",
        "original-unit-fixture",
        "approved",
        "real_demo",
    )


@KNOWN_RANK
def test_wireless_phrase_should_rank_matching_product_before_same_category_wired_product():
    wired = simulated_product("a-wired", "Bàn phím có dây")
    wireless = simulated_product("z-wireless", "Bàn phím không dây")
    rep = PARSER.parse("tôi muốn bàn phím không dây", "voice")
    ranked = RankingService().rank(rep, [wired, wireless])
    assert ranked[0].product.id == wireless.id


@KNOWN_RANK
def test_shape_words_should_not_tie_every_product_in_an_explicit_category():
    rectangular = simulated_product("a-rectangular", "Bàn chữ nhật", "Bàn", "abo-ban")
    round_table = replace(rectangular, id="z-round", name_vi="Bàn tròn")
    ranked = RankingService().rank(
        PARSER.parse("tôi muốn một cái bàn tròn nhỏ để trong phòng ngủ của mình", "voice"),
        [rectangular, round_table],
    )
    assert ranked[0].product.id == round_table.id


@KNOWN_RANK
def test_polite_filler_should_not_erase_short_product_request_without_exact_category():
    shoe = simulated_product("shoe", "Giày nam", "Giày nam", "abo-giay-nam")
    # Generic "giày" is not an exact category name in the real-demo tree.
    bare = RankingService().rank(PARSER.parse("giày", "voice"), [shoe])
    conversational = RankingService().rank(
        PARSER.parse("cho mình xem một đôi giày để đi làm mỗi ngày được không", "voice"),
        [shoe],
    )
    assert bare and conversational


@pytest.mark.parametrize(
    "text,forbidden",
    [
        ("bạn có thể cho mình xem một đôi giày được không", "abo-ban"),
        ("xin chào mình muốn mua loa", "abo-chao"),
        ("gói quà cho mình đôi giày", "abo-goi"),
        ("mua giày có cần đặt cọc không", "abo-coc"),
    ],
)
def test_politely_spoken_homographs_do_not_invent_another_product_category(text, forbidden):
    c = constraints(text).get("category")
    assert c is None or c.value != forbidden
