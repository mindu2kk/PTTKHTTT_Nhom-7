from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from app.application.image_search import ImageSearchService
from app.application.search import RankingService, SearchOrchestrator, SearchService
from app.domain.catalog import Product
from app.domain.media import CleanImage, EncodedImage, MediaError
from app.domain.search import FilterConstraint, QueryRepresentation, SearchOptions


def product(identifier, name="Tai nghe đen", price=499999, quantity=1):
    return Product(
        identifier,
        identifier,
        name,
        "",
        "headphones",
        "Tai nghe",
        price,
        quantity,
        "/image",
        "Ảnh thử",
        "đen",
        "nhựa",
        "",
        None,
        "verified",
        "demo",
        "source",
        "approved",
        "real_demo",
    )


@pytest.mark.parametrize(
    "key,operator,value,expected",
    [
        ("price_max", "lt", 500000, 499999),
        ("price_max", "lte", 500000, 500000),
        ("price_min", "gt", 500000, 500001),
        ("price_min", "gte", 500000, 500000),
    ],
)
async def test_retrieval_translates_strict_boundaries_before_repository(
    key, operator, value, expected
):
    repository = AsyncMock()
    repository.list_products.return_value = ([], 0)
    rep = QueryRepresentation(
        "voice",
        hard_filters=(
            FilterConstraint("category", "headphones", "ui_selected", 1),
            FilterConstraint(key, value, "explicit_text", 1, operator),
        ),
    )
    await SearchService(repository).retrieve(rep)
    filters = repository.list_products.call_args.args[0]
    assert getattr(filters, key) == expected
    assert filters.categories == ("headphones",)


def test_lexical_rank_discards_unrelated_product_and_keeps_stock_last():
    rows = [
        product("empty", quantity=0),
        replace(product("wrong", "Bàn gỗ"), category_name="Gia dụng"),
        product("available"),
    ]
    result = RankingService().rank(QueryRepresentation("text", normalized_text="tai nghe"), rows)
    assert [r.product.id for r in result] == ["available", "empty"]


async def test_no_relaxation_of_explicit_or_ui_filters_without_consent():
    repository = AsyncMock()
    repository.categories.return_value = []
    repository.list_products.return_value = ([], 0)
    result = await SearchOrchestrator(repository).search(
        "tai nghe màu đen dưới 500k", "voice", SearchOptions(category="headphones")
    )
    assert not result.query.relaxed_filters and result.total == 0
    filters = repository.list_products.call_args.args[0]
    assert (filters.categories, filters.color, filters.price_max) == (
        ("headphones",),
        "đen",
        499999,
    )


async def test_image_vectors_cannot_add_product_outside_prefiltered_candidates():
    repository = AsyncMock()
    repository.categories.return_value = []
    repository.list_products.return_value = ([product("allowed"), product("unindexed")], 2)
    validator, encoder, index = AsyncMock(), AsyncMock(), AsyncMock()
    validator.clean_image.return_value = CleanImage(b"clean", "hash", 32, 32)
    encoder.encode.return_value = EncodedImage((1.0, 0.0), "revision-A", 1.0, 0.0)
    index.search.return_value = {"allowed": 0.8, "private-or-wrong-category": 1.0}
    result = await ImageSearchService(
        SearchOrchestrator(repository), validator, encoder, index
    ).find(
        b"image",
        "image/png",
        "image.png",
        "",
        SearchOptions(category="headphones", price_max=500000),
    )
    assert [r.product.id for r in result.items] == ["allowed"]
    index.search.assert_awaited_once_with((1.0, 0.0), "revision-A", ("allowed", "unindexed"))
    assert result.query.image_vector_ref == "revision-A"


async def test_invalid_image_never_reaches_encoder_or_index():
    validator, encoder, index = AsyncMock(), AsyncMock(), AsyncMock()
    validator.clean_image.side_effect = MediaError(422, "Ảnh không hợp lệ.")
    with pytest.raises(MediaError):
        await ImageSearchService(AsyncMock(), validator, encoder, index).find(
            b"bad", "image/png", "x.png", "", SearchOptions()
        )
    encoder.encode.assert_not_awaited()
    index.search.assert_not_awaited()


def test_visual_ranking_uses_similarity_before_lexical_name():
    rows = [product("low", "Tai nghe"), replace(product("high"), name_vi="Bàn")]
    result = RankingService().rank(QueryRepresentation("image"), rows, {"low": 0.2, "high": 0.9})
    assert [r.product.id for r in result] == ["high", "low"]


async def test_relaxation_uses_displayable_results_not_unindexed_candidate_count():
    repository = AsyncMock()
    repository.categories.return_value = []
    repository.list_products.side_effect = [
        ([product("indexed"), product("no-vector-1"), product("no-vector-2")], 3),
        ([product("indexed"), product("extra-1"), product("extra-2")], 3),
    ]
    lookup = AsyncMock(
        side_effect=[
            {"indexed": 0.9},
            {"indexed": 0.9, "extra-1": 0.8, "extra-2": 0.7},
        ]
    )
    outcome = await SearchOrchestrator(repository).search(
        "tai nghe màu đen",
        "image",
        SearchOptions(category="headphones", allow_relax=("color",)),
        image_lookup=lookup,
    )
    assert outcome.total == 3
    assert [f.key for f in outcome.query.relaxed_filters] == ["color"]
    assert [f.key for f in outcome.query.hard_filters] == ["category"]
    assert lookup.await_count == 2
    assert repository.list_products.call_args_list[0].args[0].color == "đen"
    assert repository.list_products.call_args_list[1].args[0].color is None


async def test_three_unrelated_lexical_candidates_do_not_prevent_consented_relaxation():
    repository = AsyncMock()
    repository.categories.return_value = []
    unrelated = replace(product("wrong", "Bàn gỗ"), category_name="Gia dụng")
    repository.list_products.side_effect = [([unrelated] * 3, 3), ([product("match")], 1)]
    outcome = await SearchOrchestrator(repository).search(
        "tai nghe màu đen",
        options=SearchOptions(allow_relax=("color",)),
    )
    assert [r.product.id for r in outcome.items] == ["match"]
    assert [f.key for f in outcome.query.relaxed_filters] == ["color"]


@pytest.mark.parametrize(
    "key,value,operator",
    [
        ("brand", "preferred-brand", "eq"),
        ("price_max", 500000, "lt"),
        ("price_min", 500000, "gt"),
    ],
)
def test_relaxed_brand_and_price_still_influence_tied_results(key, value, operator):
    preferred = replace(
        product("z-preferred"),
        brand="preferred-brand",
        price_vnd=600000 if key == "price_min" else 400000,
    )
    other = replace(product("a-other"), price_vnd=300000 if key == "price_min" else 600000)
    query = QueryRepresentation(
        "image", relaxed_filters=(FilterConstraint(key, value, "explicit_text", 1, operator),)
    )
    ranked = RankingService().rank(query, [other, preferred], {"a-other": 0.8, "z-preferred": 0.8})
    assert ranked[0].product.id == "z-preferred"
