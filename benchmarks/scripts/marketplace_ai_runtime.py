"""Fresh local model/BFF checks; no source audio/transcript redistributed."""

import json
import time
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/marketplace-ai"
QUERIES = [
    ("chỗ ngồi", ["Ghế", "Ghế sofa"]),
    ("chỗ ngồi bọc vải", ["Ghế", "Ghế sofa"]),
    ("chỗ ngồi tối giản", ["Ghế", "Ghế sofa"]),
    ("đồ chiếu sáng", ["Đèn bàn"]),
    ("đồ chiếu sáng tối giản", ["Đèn bàn"]),
    ("đồ chiếu sáng màu trắng", ["Đèn bàn"]),
    ("đồ lót sàn", ["Thảm"]),
    ("đồ lót sàn mềm", ["Thảm"]),
    ("đồ lót sàn hình học", ["Thảm"]),
    ("đồ tựa đầu", ["Gối"]),
    ("đồ tựa đầu bọc vải", ["Gối"]),
    ("đồ tựa đầu tối giản", ["Gối"]),
    ("vỏ bảo vệ điện thoại", ["Ốp điện thoại"]),
    ("vỏ bảo vệ điện thoại tối giản", ["Ốp điện thoại"]),
    ("đồ mang chân", ["Giày nam", "Giày nữ"]),
    ("đồ mang chân thể thao", ["Giày nam", "Giày nữ"]),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    with httpx.Client(
        base_url="http://localhost:3000",
        timeout=65,
        headers={"Origin": "http://localhost:3000"},
    ) as client:
        warmup = client.post(
            "/api/v1/search/describe", json={"q": "sofa", "page_size": 5}
        )
        warmup.raise_for_status()
        # Cache-equivalent prompts are reported separately, never mixed into encoder latency.
        for query, relevant in QUERIES:
            start = time.perf_counter()
            response = client.post(
                "/api/v1/search/describe", json={"q": query, "page_size": 5}
            )
            latency = (time.perf_counter() - start) * 1000
            response.raise_for_status()
            data = response.json()
            categories = [r["product"]["category_name"] for r in data["items"]]
            rows.append(
                {
                    "q": query,
                    "relevant_categories": relevant,
                    "status": response.status_code,
                    "http_ms": round(latency, 3),
                    "cached": data["media"]["cached"],
                    "media": data["media"],
                    "hard_filters": data["query"]["hard_filters"],
                    "top5_categories": categories,
                    "top5_ids": [r["product"]["id"] for r in data["items"]],
                    "top1_category_match": bool(
                        categories and categories[0] in relevant
                    ),
                    "precision_at_5": sum(c in relevant for c in categories) / 5,
                }
            )
        cases = {
            "unknown": {"q": "zzqqy vô nghĩa"},
            "order_intent": {"q": "tra cứu đơn hàng 123456"},
            "invalid_range": {"q": "ghế", "price_min": 10, "price_max": 1},
        }
        guards = {}
        for name, body in cases.items():
            r = client.post("/api/v1/search/describe", json=body)
            assert r.status_code == 422
            guards[name] = r.status_code
        cross_origin = client.post(
            "/api/v1/search/compare",
            json={"ids": ["a", "b"]},
            headers={"Origin": "https://untrusted.invalid"},
        )
        assert cross_origin.status_code == 403
        guards["cross_origin_bff"] = cross_origin.status_code
        # Reuse established ASR/media scenarios; write only into this new evidence directory.
        import m8_media_checks

        m8_media_checks.OUT = OUT
        m8_media_checks.main()
    fresh = [r["http_ms"] for r in rows if not r["cached"]]
    cached = [r["http_ms"] for r in rows if r["cached"]]
    result = {
        "scope": "16 hand-authored finite-Vietnamese-concept prompts. Source-category proxy relevance, not independent human judgments or general Vietnamese understanding. Cache-equivalent prompts separated.",
        "query_count": len(rows),
        "uncached_count": len(fresh),
        "warm_uncached_p50_ms": round(float(np.percentile(fresh, 50)), 3),
        "warm_uncached_p95_ms": round(float(np.percentile(fresh, 95)), 3),
        "cached_count": len(cached),
        "top1_category_match_rate": sum(r["top1_category_match"] for r in rows)
        / len(rows),
        "mean_precision_at_5": sum(r["precision_at_5"] for r in rows) / len(rows),
        "guards": guards,
        "results": rows,
    }
    (OUT / "runtime.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "results"}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
