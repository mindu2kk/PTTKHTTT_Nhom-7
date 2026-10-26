import pytest

from app.application.query_parser import RuleQueryParser
from app.application.shopping_assistant import visual_prompt
from app.domain.catalog import Category
from app.domain.menswear import MENSWEAR_GROUPS


def menswear_categories():
    categories = [Category("nam", None, "nam", "Thời trang nam", 0, 0)]
    for order, (group, name, leaves) in enumerate(MENSWEAR_GROUPS):
        categories.append(Category(group, "nam", group, name, 1, order))
        categories.extend(
            Category(cid, group, cid, label, 2, index)
            for index, (cid, label, _) in enumerate(leaves)
        )
    return categories


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (alias, cid)
        for _, _, leaves in MENSWEAR_GROUPS
        for cid, _, aliases in leaves
        for alias in aliases
    ],
)
def test_menswear_search_names(text, expected):
    parsed = RuleQueryParser(menswear_categories()).parse(f"tìm {text}")
    assert next(f.value for f in parsed.hard_filters if f.key == "category") == expected


def test_category_images_have_exact_group_counts():
    assert [len(leaves) for _, _, leaves in MENSWEAR_GROUPS] == [7, 5, 7]
    assert len({c.id for c in menswear_categories()}) == 23


@pytest.mark.parametrize(
    ("text", "concept"),
    [
        ("áo pull đen", "t-shirt"),
        ("quần khaki nam", "khaki trousers"),
        ("kính mắt", "eyeglasses"),
        ("dây lưng", "belt"),
    ],
)
def test_menswear_visual_description_mapping(text, concept):
    assert concept in visual_prompt(text)
