import pytest

from app.infrastructure.shop_sample import split_options, validate


def test_option_lists_preserve_all_sizes_and_unknowns():
    assert split_options("M, L, XL, L ") == ["M", "L", "XL"]
    assert split_options("Chưa có thông tin") == []
    assert split_options("38, 39, 40, 41, 42, 43, 44, 45") == [str(n) for n in range(38, 46)]


def sample_record():
    return {
        "name": "Sản phẩm mô phỏng kiểm thử",
        "description": "Dữ liệu test gốc",
        "category_id": "nam-ao-so-mi",
        "size": "L",
        "color": "Trắng",
        "price_vnd": 260000,
        "trial_stock": 8,
        "image_url": "https://i.postimg.cc/test/original.jpg",
        "source_url": "https://rhodi.vn/test-p9900001.html",
    }


def test_source_product_id_is_not_a_guessed_sku():
    assert validate(sample_record(), True) == "p9900001"


def test_unreviewed_source_rejected():
    with pytest.raises(ValueError, match="quyền"):
        validate(sample_record(), False)


def test_native_rhodi_image_still_requires_explicit_rights_review():
    record = {
        **sample_record(),
        "image_url": "https://pos.nvncdn.com/afec53-228676/ps/Somi.jpg?v=1790932084",
    }
    assert validate(record, True) == "p9900001"
    with pytest.raises(ValueError, match="quyền"):
        validate(record, False)


@pytest.mark.parametrize(
    "url",
    [
        "http://i.postimg.cc/test.jpg",
        "https://evil.invalid/a.jpg",
        "https://i.postimg.cc.evil.invalid/a.jpg",
        "https://i.postimg.cc@127.0.0.1/a.jpg",
        "https://i.postimg.cc:443/a.jpg",
        "https://postimg.cc/abc",
        "file:///etc/passwd",
    ],
)
def test_nonallowlisted_image_urls_rejected(url):
    with pytest.raises(ValueError):
        validate({**sample_record(), "image_url": url}, True)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("price_vnd", 1.5),
        ("price_vnd", 0),
        ("trial_stock", -1),
        ("trial_stock", True),
        ("size", ""),
        ("name", ""),
        ("source_url", "https://other.invalid/test-p1.html"),
    ],
)
def test_invalid_sample_rejected(field, value):
    with pytest.raises(ValueError):
        validate({**sample_record(), field: value}, True)
