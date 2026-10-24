"""Actual media/text requests with business-table hashes before and after."""

import asyncio
import hashlib
import json
from pathlib import Path

import httpx
from sqlalchemy import text

from app.infrastructure.database import engine, session_factory

ROOT = Path(__file__).resolve().parents[2]
TABLES = [
    "products",
    "product_variants",
    "seller_offers",
    "inventory",
    "carts",
    "cart_items",
    "orders",
    "order_items",
    "mock_payments",
    "stock_reservations",
    "shipments",
]


async def snapshot():
    async with session_factory() as s:
        return {
            table: hashlib.sha256(
                "\n".join(
                    (
                        await s.execute(
                            text(
                                f"SELECT row_to_json(t)::text FROM {table} t ORDER BY 1"
                            )
                        )
                    )
                    .scalars()
                    .all()
                ).encode()
            ).hexdigest()
            for table in TABLES
        }


async def run():
    try:
        before = await snapshot()
        async with httpx.AsyncClient(
            base_url="http://127.0.0.1:8000", timeout=65
        ) as client:
            requests = []
            for q, modality in [
                ("áo len nam màu đen dưới 500k", "text"),
                ("tôi muốn mua áo mùa đông", "voice"),
            ]:
                r = await client.post(
                    "/api/v1/search/text", json={"q": q, "modality": modality}
                )
                r.raise_for_status()
                requests.append({"modality": modality, "status": r.status_code})
            for endpoint, field, path, mime in [
                (
                    "image",
                    "image",
                    ROOT / "benchmarks/images/navy-sweater-heldout.png",
                    "image/png",
                ),
                (
                    "voice",
                    "audio",
                    ROOT / "benchmarks/audio/course-tts.wav",
                    "audio/wav",
                ),
            ]:
                r = await client.post(
                    "/api/v1/search/" + endpoint,
                    files={field: (path.name, path.read_bytes(), mime)},
                )
                r.raise_for_status()
                requests.append({"modality": endpoint, "status": r.status_code})
        after = await snapshot()
        assert before == after, "Search changed business state"
        (ROOT / "docs/evidence/tc6-media-readonly.json").write_text(
            json.dumps(
                {
                    "result": "passed",
                    "tables": TABLES,
                    "before": before,
                    "after": after,
                    "actual_requests": requests,
                    "owned_order_readonly": "separate real PostgreSQL integration test test_tc5_owner_and_tc6_read_only",
                },
                indent=2,
            ),
            encoding="utf8",
        )
        print("TC6 actual text/edited voice/CLIP/ASR business-table hashes unchanged")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
