"""Warm, uncached full HTTP image path on licensed photos; latency, not relevance."""

import io
import json
import math
import time
import uuid
from pathlib import Path

import httpx
from PIL import Image

from photo_eval import prepare

ROOT = Path(__file__).resolve().parents[2]


def main():
    samples, manifest = prepare()
    queries = [s for s in samples if s["split"] == "query"]
    nonce = uuid.uuid4().bytes
    measurements = []
    with httpx.Client(
        base_url="http://localhost:8000", timeout=65, trust_env=False
    ) as client:
        for index, sample in enumerate([queries[0], *queries]):
            image = Image.open(io.BytesIO(sample["raw"])).convert("RGB")
            image.putpixel(
                (0, 0), tuple(nonce[(index + j) % len(nonce)] for j in range(3))
            )
            image.putpixel((1, 0), (index, nonce[0], nonce[1]))
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            started = time.perf_counter()
            response = client.post(
                "/api/v1/search/image",
                files={"image": ("query.png", buffer.getvalue(), "image/png")},
            )
            response.raise_for_status()
            data = response.json()
            assert data["media"]["cached"] is False
            assert all(
                row["product"]["verification_status"] == "verified"
                for row in data["items"]
            )
            measurement = {
                "id": sample["id"],
                "bytes": len(buffer.getvalue()),
                "http_ms": round((time.perf_counter() - started) * 1000, 3),
                "service_ms": data["latency_ms"],
                "stages_ms": data["stages_ms"],
            }
            if index:
                measurements.append(measurement)
            else:
                warmup = measurement
    report = {
        "scope": "25 distinct licensed photo inputs, original 50-product main demo catalog, full HTTP validation/encode/SQL/vector/ranking/serialize; latency only, not relevance accuracy",
        "source": manifest["source"],
        "cache_control": "Run-specific two pixels differ per image so embedding cache is not reused; all cached=false. Model warmup excluded.",
        "warmup": warmup,
        "percentiles_ms": {
            f"p{n}": sorted(m["http_ms"] for m in measurements)[
                math.ceil(len(measurements) * n / 100) - 1
            ]
            for n in [50, 90, 95, 99]
        },
        "measurements": measurements,
    }
    (ROOT / "docs/evidence/warm-image-http.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps(report["percentiles_ms"]))


if __name__ == "__main__":
    main()
