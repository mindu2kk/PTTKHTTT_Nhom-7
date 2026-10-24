import json
from pathlib import Path

import pytest
from httpx import AsyncClient

from app.application.query_parser import RuleQueryParser, amount, normalize
from app.domain.catalog import Category
from app.domain.search import SearchOptions

FIXTURE = Path(__file__).resolve().parents[3] / "benchmarks/fixtures/catalog.json"
CATEGORIES = [Category(**c) for c in json.loads(FIXTURE.read_text(encoding="utf-8"))["categories"]]
PARSER = RuleQueryParser(CATEGORIES)


@pytest.mark.parametrize(
    "phrase,value",
    [
        ("500k", 500000),
        ("500 nghìn", 500000),
        ("500 ngàn", 500000),
        ("năm trăm nghìn", 500000),
        ("năm trăm k", 500000),
        ("2tr", 2000000),
        ("2 triệu", 2000000),
        ("2 củ", 2000000),
        ("hai triệu", 2000000),
        ("1,5tr", 1500000),
        ("1.5 triệu", 1500000),
        ("150000", 150000),
        ("ba trăm ngàn", 300000),
        ("hai mươi nghìn", 20000),
        ("mèo", None),
    ],
)
def test_amount_oracle(phrase, value):
    assert amount(phrase) == value


@pytest.mark.parametrize(
    "category,expected",
    [
        ("áo len nam", "ao-len-nam"),
        ("ao len nam", "ao-len-nam"),
        ("ÁO LEN NAM", "ao-len-nam"),
        ("mens sweater", "ao-len-nam"),
        ("áo phông nam", "ao-thun-nam"),
        ("ao thun nu", "ao-thun-nu"),
        ("giày thể thao", "giay-the-thao"),
        ("sneaker", "giay-the-thao"),
        ("túi đeo chéo", "tui-deo-cheo"),
        ("áo sơ mi nam", "ao-so-mi-nam"),
    ],
)
@pytest.mark.parametrize(
    "money_text,operator",
    [("dưới 500k", "lt"), ("không quá 500 nghìn", "lte"), ("under 500k", "lt")],
)
def test_parser_category_money_variants(category, expected, money_text, operator):
    rep = PARSER.parse(f"{category} màu đen {money_text}")
    constraints = {c.key: c for c in rep.hard_filters}
    assert constraints["category"].value == expected
    assert constraints["color"].value == "đen"
    assert constraints["color"].origin == "explicit_text"
    assert constraints["price_max"].value == 500000
    assert constraints["price_max"].operator == operator


@pytest.mark.parametrize(
    "text,key,value,op",
    [
        ("áo len trên 200k", "price_min", 200000, "gt"),
        ("áo từ 200 nghìn", "price_min", 200000, "gte"),
        ("áo size XL", "size", "XL", "eq"),
        ("áo màu navy", "color", "xanh than", "eq"),
        ("áo white", "color", "trắng", "eq"),
        ("áo chất liệu cotton", "material", "cotton", "eq"),
        ("giày Nike", "brand", "nike", "eq"),
        ("áo nữ", "gender", "nữ", "eq"),
    ],
)
def test_attribute_cases(text, key, value, op):
    c = next(c for c in PARSER.parse(text).hard_filters if c.key == key)
    assert (c.value, c.operator) == (value, op)


def test_soft_and_ambiguous_prices_not_hard():
    rep = PARSER.parse("tôi muốn mua áo mùa đông khoảng năm trăm nghìn", "voice")
    assert rep.modality == "voice"
    assert all(c.key not in {"price_max", "price_min", "gender"} for c in rep.hard_filters)
    assert {(c.key, c.value) for c in rep.soft_preferences} == {
        ("season", "mùa đông"),
        ("price_target", 500000),
    }
    assert not any(c.key.startswith("price") for c in PARSER.parse("áo 500k").hard_filters)
    assert normalize("Đầm nữ") == "dam nu"
    assert PARSER.parse("Đầm nữ").raw_text == "Đầm nữ"


def test_ui_priority():
    rep = PARSER.parse(
        "áo len nam đen dưới 500k",
        options=SearchOptions(category="ao-nam", color="đỏ", price_max=900000),
    )
    values = {c.key: c for c in rep.hard_filters}
    assert values["category"].value == "ao-nam"
    assert values["color"].value == "đỏ" and values["color"].origin == "ui_selected"
    assert values["price_max"].value == 900000 and values["price_max"].operator == "lte"


async def test_tc1_actual_api(client: AsyncClient):
    response = await client.post("/api/v1/search/text", json={"q": "áo len nam màu đen dưới 500k"})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["total"] == 10
    assert [r["product"]["price_vnd"] for r in data["items"][:3]] == [264000, 324000, 456000]
    assert all(
        r["product"]["color"] == "đen" and r["product"]["price_vnd"] < 500000 for r in data["items"]
    )
    assert data["items"][-1]["product"]["available_quantity"] == 0


async def test_tc4_expansion_requires_consent_and_preserves_ui(client: AsyncClient):
    body = {"q": "túi đeo chéo màu đỏ dưới 150k"}
    strict = (await client.post("/api/v1/search/text", json=body)).json()
    assert strict["total"] == 1 and not strict["query"]["relaxed_filters"]
    expanded = (
        await client.post("/api/v1/search/text", json={**body, "allow_relax": ["color"]})
    ).json()
    assert expanded["total"] == 3
    assert expanded["items"][0]["product"]["price_vnd"] == 95000
    assert expanded["query"]["relaxed_filters"][0]["key"] == "color"
    assert expanded["query"]["relaxed_filters"][0]["origin"] == "explicit_text"
    assert all(
        r["product"]["price_vnd"] < 150000 and r["product"]["category_id"] == "tui-deo-cheo"
        for r in expanded["items"]
    )
    fixed = (
        await client.post(
            "/api/v1/search/text", json={**body, "allow_relax": ["color"], "color": "đỏ"}
        )
    ).json()
    assert fixed["total"] == 1 and not fixed["query"]["relaxed_filters"]


async def test_winter_voice_transcript_path_not_asr_proof(client: AsyncClient):
    response = await client.post(
        "/api/v1/search/text", json={"q": "tôi muốn mua áo mùa đông", "modality": "voice"}
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["query"]["modality"] == "voice"
    assert any(c["key"] == "season" for c in data["query"]["soft_preferences"])
    assert "phao" in normalize(data["items"][0]["product"]["name_vi"])


async def test_empty_sqli_and_order_intent(client: AsyncClient):
    for q in ["mèo bay ngoài hành tinh", "' OR 1=1 --", "<script>alert(1)</script>"]:
        response = await client.post("/api/v1/search/text", json={"q": q})
        assert response.status_code == 200
        assert response.json()["total"] == 0
    response = await client.get("/api/v1/search/text", params={"q": "kiểm tra đơn hàng 20261005"})
    assert response.status_code == 401
    assert "710500" not in response.text


async def test_search_readonly(client: AsyncClient):
    from app.infrastructure.database import session_factory
    from tests.test_catalog import snapshot

    async with session_factory() as session:
        before = await snapshot(session)
    await client.post("/api/v1/search/text", json={"q": "áo len nam"})
    await client.get("/api/v1/search/suggestions", params={"q": "áo"})
    async with session_factory() as session:
        assert await snapshot(session) == before


async def test_category_and_price_homographs_do_not_invent_attributes(client: AsyncClient):
    for q, forbidden in [("Giày búp bê", "color"), ("áo len nam tối đa năm trăm k", "material")]:
        response = await client.get("/api/v1/search/text", params={"q": q})
        assert response.status_code == 200
        data = response.json()
        assert data["total"] > 0
        assert not any(c["key"] == forbidden for c in data["query"]["hard_filters"])
