"""Actual CLIP/API test on an original held-out illustration, not a real-world photo claim."""

import io
import json
import math
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
image = Image.new("RGB", (640, 640), "#dbdce0")
draw = ImageDraw.Draw(image)
draw.polygon(
    [
        (230, 120),
        (150, 160),
        (65, 300),
        (145, 345),
        (200, 270),
        (200, 535),
        (440, 535),
        (440, 270),
        (495, 345),
        (575, 300),
        (490, 160),
        (410, 120),
        (385, 155),
        (320, 180),
        (255, 155),
    ],
    fill="#233c58",
)
draw.arc((240, 88, 400, 205), 0, 180, fill="#485c71", width=11)
draw.line([(210, 500), (430, 500)], fill="#485c71", width=8)
buffer = io.BytesIO()
image.save(buffer, "PNG")
raw = buffer.getvalue()
path = ROOT / "benchmarks/images/navy-sweater-heldout.png"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_bytes(raw)
times = []
with httpx.Client(
    base_url="http://localhost:8000", timeout=65, trust_env=False
) as client:
    for i in range(10):
        t = time.perf_counter()
        response = client.post(
            "/api/v1/search/image", files={"image": ("navy.png", raw, "image/png")}
        )
        assert response.status_code == 200, response.text
        result = response.json()
        times.append((time.perf_counter() - t) * 1000)
        assert result["query"]["modality"] == "image"
        assert result["items"][0]["product"]["category_id"] == "ao-len-nam", result[
            "items"
        ][:3]
    filtered = client.post(
        "/api/v1/search/image",
        files={"image": ("navy.png", raw, "image/png")},
        data={"category": "tui-deo-cheo", "price_max": "150000"},
    )
    filtered.raise_for_status()
    assert all(
        r["product"]["category_id"] == "tui-deo-cheo"
        and r["product"]["price_vnd"] <= 150000
        for r in filtered.json()["items"]
    )
    malformed = client.post(
        "/api/v1/search/image",
        files={"image": ("bad.png", b"not an image", "image/png")},
    )
    assert malformed.status_code == 422
    output = {
        "result": "passed",
        "encoder": "actual OpenCLIP ViT-B/32 CPU",
        "query_fixture": "original held-out illustration; not a real photograph",
        "top_three": [
            {"id": r["product"]["id"], "score": r["score"]} for r in result["items"][:3]
        ],
        "first_http_ms": round(times[0], 3),
        "repeated_http_p95_ms": round(
            sorted(times[1:])[math.ceil(len(times[1:]) * 0.95) - 1], 3
        ),
        "cache_note": "Repeats reuse sanitized-image embedding cache; first query runs model; not 10 uncached inference measurements",
        "metadata": result["media"],
        "filtered_candidates": filtered.json()["total"],
        "bad_file_status": malformed.status_code,
    }
    (ROOT / "docs/evidence/image-integration.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(output, ensure_ascii=True, indent=2))
