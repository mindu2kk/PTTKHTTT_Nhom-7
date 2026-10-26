import hashlib
import io
import runpy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from PIL import Image

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/index_real_images.py"


def test_index_prepares_the_same_image_content_as_upload_validation():
    module = runpy.run_path(str(SCRIPT))
    buffer = io.BytesIO()
    Image.new("RGB", (100, 100), "navy").save(buffer, "JPEG")
    raw = buffer.getvalue()
    expected = module["sanitize"](raw, "image/jpeg", "catalog.jpg")
    actual = module["prepare_image"](raw, "https://i.postimg.cc/test/no-extension")
    assert actual == expected
    assert actual.sha256 == hashlib.sha256(actual.content).hexdigest()


async def test_index_closes_database_engine_even_if_encoding_fails(monkeypatch):
    module = runpy.run_path(str(SCRIPT))
    dispose = AsyncMock()
    monkeypatch.setitem(module["main"].__globals__, "engine", SimpleNamespace(dispose=dispose))
    monkeypatch.setitem(
        module["main"].__globals__,
        "index_catalog",
        AsyncMock(side_effect=RuntimeError("worker error")),
    )
    with pytest.raises(RuntimeError, match="worker error"):
        await module["main"]()
    dispose.assert_awaited_once()
