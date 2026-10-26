from app.domain.sizes import product_sizes


def test_sizes_keep_declared_options_in_order():
    assert product_sizes("M, S, L, XL, 2XL, M") == ["S", "M", "L", "XL", "XXL"]
    assert product_sizes("F") == ["F"]
    assert product_sizes("Chưa có thông tin") == ["F"]
    assert product_sizes("Phiên bản nguồn") == ["F"]
