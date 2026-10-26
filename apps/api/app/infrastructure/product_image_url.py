"""Inspect direct product image URLs without storing files or following redirects."""

import hashlib
import io
from typing import Any
from urllib.parse import urlsplit

import httpx
from PIL import Image


def validate_image_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "i.postimg.cc"
        or parsed.fragment
        or len(url) > 2048
    ):
        raise ValueError("Hãy dùng URL ảnh trực tiếp HTTPS từ i.postimg.cc, tối đa 2048 ký tự.")


async def fetch_image(url: str) -> bytes:
    validate_image_url(url)
    content = bytearray()
    # Fixed allowlisted host, no redirects/proxy, bounded bytes; no filesystem cache.
    async with httpx.AsyncClient(timeout=25, follow_redirects=False, trust_env=False) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            if response.status_code != 200:
                raise ValueError("URL ảnh không trả về ảnh trực tiếp.")
            if response.headers.get("content-type", "").split(";")[0] not in {
                "image/jpeg",
                "image/png",
                "image/webp",
            }:
                raise ValueError("URL không trả về JPEG, PNG hoặc WebP.")
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > 5 * 1024 * 1024:
                    raise ValueError("Ảnh vượt quá 5 MB.")
    return bytes(content)


async def inspect_image(url: str) -> dict[str, Any]:
    content = await fetch_image(url)
    with Image.open(io.BytesIO(content)) as photo:
        width, height = photo.size
        if photo.format not in {"JPEG", "PNG", "WEBP"} or not 256 <= width * height <= 12000000:
            raise ValueError("Nội dung hoặc kích thước ảnh không hợp lệ.")
        photo.verify()
    return {"width": width, "height": height, "sha256": hashlib.sha256(content).hexdigest()}
