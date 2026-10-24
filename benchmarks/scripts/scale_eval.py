"""3k PostgreSQL/ASGI benchmark and 204 authored structured query oracles.

Only the separate *_test database. No human semantic judgments are claimed.
Temporary scale rows are removed in finally; never reset the database.
"""

import asyncio

# ruff: noqa: E402
import json
import logging
import math
import os
import platform
import sys
import time
import uuid
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import delete, insert, select, event
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]
HTTP_TARGET = os.environ.get("BENCHMARK_API_URL")
if HTTP_TARGET and HTTP_TARGET != "http://127.0.0.1:8002":
    raise RuntimeError("HTTP benchmark only permits the isolated loopback API on 8002")
TIMING_KEY = "http_tcp_ms" if HTTP_TARGET else "http_asgi_ms"
url = (
    os.environ.get("TEST_DATABASE_URL")
    or dotenv_values(ROOT / ".env")["TEST_DATABASE_URL"]
)
if not url or not (make_url(url).database or "").endswith("_test"):
    raise RuntimeError("Requires isolated *_test database")
os.environ["DATABASE_URL"] = url
sys.path.insert(0, str(ROOT / "apps/api"))
from httpx import ASGITransport, AsyncClient
from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import (
    Inventory,
    ProductAttribute,
    ProductImage,
    ProductRow,
    ProductSource,
    ProductVariant,
    SellerOffer,
)
from app.application.query_parser import normalize
from app.main import app

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("hoodoomart.http").setLevel(logging.WARNING)
MODELS = [
    ProductRow,
    ProductVariant,
    ProductImage,
    ProductSource,
    ProductAttribute,
    SellerOffer,
    Inventory,
]
captured = {}


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def capture_plan(_conn, _cursor, statement, parameters, _context, _many):
    if (
        not statement.startswith("EXPLAIN")
        and "SELECT products.id" in statement
        and "LIMIT" in statement
    ):
        captured["search" if statement.startswith("WITH RECURSIVE") else "grid"] = [
            statement,
            parameters,
        ]


def values(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def pct(xs, p):
    return round(sorted(xs)[math.ceil(len(xs) * p) - 1], 3)


async def main():
    fixture = json.loads(
        (ROOT / "benchmarks/fixtures/catalog.json").read_text(encoding="utf8")
    )
    originals = [p for p in fixture["products"] if not p["id"].startswith("hidden-")]
    corpus = [dict(p) for p in originals]
    prefix = "scale-" + uuid.uuid4().hex[:6] + "-"
    pids = []
    batches = {m: [] for m in MODELS}
    queries = []
    results = []
    grid_results = []
    failures = []
    try:
        async with session_factory.begin() as s:
            for index in range(2950):
                base = originals[index % 34]
                old = base["id"]
                pid = prefix + f"{index:04}"
                pids.append(pid)
                # Cache source rows once per base product, reuse their approved source/image bytes.
                if index < 34:
                    base["_rows"] = {}
                    for model in MODELS:
                        column = (
                            model.id
                            if model is ProductRow
                            else model.offer_id
                            if model is Inventory
                            else model.product_id
                        )
                        key = old if model is not Inventory else "offer-" + old
                        base["_rows"][model] = [
                            values(r)
                            for r in (
                                await s.scalars(select(model).where(column == key))
                            ).all()
                        ]
                for model in MODELS:
                    for original in base["_rows"][model]:
                        row = dict(original)
                        if model is ProductRow:
                            row.update(id=pid, slug=pid)
                        if "product_id" in row:
                            row["product_id"] = pid
                        if model is ProductVariant:
                            row.update(id="variant-" + pid, sku=pid)
                        if model is ProductImage:
                            row["id"] = "image-" + pid
                        if model is SellerOffer:
                            row.update(id="offer-" + pid, variant_id="variant-" + pid)
                        if model is Inventory:
                            row.update(offer_id="offer-" + pid, reserved=0)
                        batches[model].append(row)
                derived = {k: v for k, v in base.items() if not k.startswith("_")}
                derived["id"] = pid
                corpus.append(derived)
            for model in MODELS:
                await s.execute(insert(model), batches[model])
        # First measured plan estimated 1 vs actual 3000 rows. Refresh statistics
        # after the bulk import before judging index or ANN changes.
        async with engine.begin() as connection:
            for model in MODELS:
                await connection.exec_driver_sql("ANALYZE " + model.__tablename__)
        categories = {c["id"]: c["name_vi"] for c in fixture["categories"]}
        for base in originals[:34]:
            name = categories[base["category_id"]]
            for variant, q in enumerate(
                [
                    name,
                    normalize(name),
                    "tôi muốn mua " + name,
                    name + " dưới 500k",
                    name + " tối đa năm trăm k",
                    name + " màu " + base["color"],
                ]
            ):
                relevant = {
                    p["id"]
                    for p in corpus
                    if p["category_id"] == base["category_id"]
                    and (variant != 3 or p["price_vnd"] < 500000)
                    and (variant != 4 or p["price_vnd"] <= 500000)
                    and (variant != 5 or p["color"] == base["color"])
                }
                queries.append(
                    {
                        "id": f"q{len(queries) + 1:03}",
                        "q": q,
                        "category": base["category_id"],
                        "kind": variant,
                        "relevant": sorted(relevant),
                    }
                )
        async with AsyncClient(
            transport=None if HTTP_TARGET else ASGITransport(app=app),
            base_url=HTTP_TARGET or "http://benchmark",
            timeout=30,
            trust_env=False,
        ) as client:
            assert (await client.get("/api/v1/products")).json()["total"] == 3000
            for concurrency in [1, 5, 10]:
                gate = asyncio.Semaphore(concurrency)

                async def query(case):
                    async with gate:
                        t = time.perf_counter()
                        r = await client.post(
                            "/api/v1/search/text",
                            json={"q": case["q"], "page_size": 10},
                        )
                        r.raise_for_status()
                        data = r.json()
                        return {
                            "http_ms": (time.perf_counter() - t) * 1000,
                            "service_ms": data["latency_ms"],
                            "ids": [x["product"]["id"] for x in data["items"]],
                            "total": data["total"],
                        }

                await asyncio.gather(*[query(q) for q in queries[:10]])
                measured = await asyncio.gather(*[query(q) for q in queries])
                quality = []
                for case, got in zip(queries, measured, strict=True):
                    rel = set(case["relevant"])
                    ids = got["ids"]
                    gains = [int(pid in rel) for pid in ids]
                    dcg = sum(g / math.log2(i + 2) for i, g in enumerate(gains))
                    ideal = sum(1 / math.log2(i + 2) for i in range(min(10, len(rel))))
                    if (ideal and dcg / ideal < 0.999) or (not ideal and ids):
                        failures.append(
                            {
                                "q": case["q"],
                                "expected_count": len(rel),
                                "actual_total": got["total"],
                                "top": ids,
                                "concurrency": concurrency,
                            }
                        )
                    quality.append(
                        {
                            "precision10": sum(gains) / 10,
                            "recall10": sum(gains) / len(rel) if rel else 1,
                            "ndcg10": dcg / ideal if ideal else int(not ids),
                            "hard_filter_leaks": sum(pid not in rel for pid in ids),
                        }
                    )
                results.append(
                    {
                        "concurrency": concurrency,
                        "success": len(measured),
                        TIMING_KEY: {
                            f"p{n}": pct([m["http_ms"] for m in measured], n / 100)
                            for n in [50, 90, 95, 99]
                        },
                        "service_ms": {
                            f"p{n}": pct([m["service_ms"] for m in measured], n / 100)
                            for n in [50, 90, 95, 99]
                        },
                        "quality": {
                            key: sum(q[key] for q in quality)
                            / (1 if key == "hard_filter_leaks" else len(quality))
                            for key in quality[0]
                        },
                    }
                )
                print(json.dumps(results[-1]), flush=True)
            async with engine.connect() as connection:
                plan = {}
                for key, (statement, parameters) in list(captured.items()):
                    plan[key] = (
                        await connection.exec_driver_sql(
                            "EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + statement,
                            parameters,
                        )
                    ).scalar_one()
                if plan:
                    (ROOT / "docs/evidence/scale-query-plan.json").write_text(
                        json.dumps(plan, indent=2), encoding="utf8"
                    )
            for concurrency in [1, 5, 10]:
                gate = asyncio.Semaphore(concurrency)

                async def grid_request(index):
                    async with gate:
                        t = time.perf_counter()
                        r = await client.get(
                            "/api/v1/products", params={"page": 1 + index % 10}
                        )
                        r.raise_for_status()
                        return (time.perf_counter() - t) * 1000

                await asyncio.gather(*[grid_request(i) for i in range(10)])
                timings = await asyncio.gather(*[grid_request(i) for i in range(100)])
                grid_results.append(
                    {
                        "concurrency": concurrency,
                        "success": len(timings),
                        TIMING_KEY: {
                            f"p{n}": pct(timings, n / 100) for n in [50, 90, 95, 99]
                        },
                    }
                )
        target = ROOT / "benchmarks/qrels"
        target.mkdir(exist_ok=True)
        (
            target
            / ("synthetic-204-http.json" if HTTP_TARGET else "synthetic-204.json")
        ).write_text(
            json.dumps(
                {
                    "construction": "204 authored templates, 34 original leaf categories x six forms; structured reference judgments, no human semantic label claim",
                    "queries": queries,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf8",
        )
        report = {
            "platform": platform.platform(),
            "public_products": 3000,
            "stored_products": 3005,
            "source": "2950 clones of original CC0 fixture; not real merchant records",
            "protocol": "Windows HTTPX over real loopback TCP to isolated Docker API/Python3.12 + Docker PostgreSQL test DB"
            if HTTP_TARGET
            else "native Windows API via HTTPX ASGITransport to actual Docker PostgreSQL; excludes TCP/HTTP server overhead",
            "query_count": len(queries),
            "qrels": "structured independent expected category/color/price oracles, not a human relevance study",
            "runs": results,
            "grid_runs": grid_results,
            "failures": failures,
            "limitations": [
                "Warm only; model inference excluded",
                "No hybrid text embedding model",
                "Reused images are scale fixtures, not image evaluation",
                "Tiny repeated vocabulary is easier than a real catalog",
            ],
        }
        (
            ROOT
            / "docs/evidence"
            / ("scale-3000-http.json" if HTTP_TARGET else "scale-3000.json")
        ).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    finally:
        async with session_factory.begin() as s:
            for model in reversed(MODELS):
                column = (
                    model.id
                    if model is ProductRow
                    else model.offer_id
                    if model is Inventory
                    else model.product_id
                )
                ids = ["offer-" + p for p in pids] if model is Inventory else pids
                await s.execute(delete(model).where(column.in_(ids)))
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
