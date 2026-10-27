import hashlib
import io

import httpx
import pytest
from PIL import Image

from app.infrastructure import product_image_url


@pytest.mark.parametrize(
    "url",
    [
        "http://i.postimg.cc/a.jpg",
        "https://127.0.0.1/a.jpg",
        "https://localhost/a.jpg",
        "https://i.postimg.cc.evil.invalid/a.jpg",
        "https://i.postimg.cc@127.0.0.1/a.jpg",
        "https://i.postimg.cc:443/a.jpg",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "https://pos.nvncdn.com/another-store/ps/a.jpg",
        "https://pos.nvncdn.com/afec53-228676/store/a.jpg",
        "https://pos.nvncdn.com/afec53-228676/ps/../a.jpg",
        "https://pos.nvncdn.com/afec53-228676/ps/%2e%2e%2fa.jpg",
        "https://pos.nvncdn.com/afec53-228676/ps/a.jpg?url=http://localhost",
        "https://pos.nvncdn.com.evil.invalid/afec53-228676/ps/a.jpg",
        "https://pos.nvncdn.com@127.0.0.1/afec53-228676/ps/a.jpg",
    ],
)
def test_rejects_unsafe_image_url_before_network(url):
    with pytest.raises(ValueError):
        product_image_url.validate_image_url(url)


def test_allows_only_the_reviewed_rhodi_product_image_location():
    product_image_url.validate_image_url(
        "https://pos.nvncdn.com/afec53-228676/ps/Somi-tho-tui-8103-QS.jpg?v=1790932084"
    )


def mock_response(monkeypatch, status, content_type, content):
    original = httpx.AsyncClient

    def client(**kwargs):
        assert kwargs["follow_redirects"] is False and kwargs["trust_env"] is False
        return original(
            **kwargs,
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    status,
                    headers={"content-type": content_type, "location": "http://127.0.0.1/"},
                    content=content,
                )
            ),
        )

    monkeypatch.setattr(product_image_url.httpx, "AsyncClient", client)


async def test_valid_image_returns_verified_dimensions_and_hash(monkeypatch):
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "black").save(buffer, format="PNG")
    content = buffer.getvalue()
    mock_response(monkeypatch, 200, "image/png", content)
    result = await product_image_url.inspect_image("https://i.postimg.cc/test/photo.png")
    assert result == {"width": 32, "height": 32, "sha256": hashlib.sha256(content).hexdigest()}


@pytest.mark.parametrize(
    "status,content_type,content",
    [
        (302, "image/png", b""),
        (200, "text/html", b"<html>not an image</html>"),
        (200, "image/png", b"not an image"),
        (200, "image/png", b"x" * (5 * 1024 * 1024 + 1)),
    ],
    ids=["redirect", "html", "invalid-image", "over-5mb"],
)
async def test_rejects_redirect_wrong_type_invalid_and_oversized_bytes(
    monkeypatch, status, content_type, content
):
    mock_response(monkeypatch, status, content_type, content)
    with pytest.raises((httpx.HTTPError, ValueError, OSError)):
        await product_image_url.inspect_image("https://i.postimg.cc/test/photo.png")
