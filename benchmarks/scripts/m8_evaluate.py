"""New M8 HTTP measurements and source-ID qrels. Never reuse M7 latency numbers."""

import argparse
import asyncio
import csv
import gzip
import hashlib
import io
import json
import math
import statistics
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

import httpx
from PIL import Image, ImageDraw
from sqlalchemy import event, func, select, text

from app.core.dependencies import CATALOG_MEDIA_ROOT
from app.domain.catalog import CatalogFilter
from app.infrastructure.catalog import SqlCatalogRepository
from app.infrastructure.database import engine, session_factory
from app.infrastructure.media import CLIP_REVISION
from app.infrastructure.models import (
    ImageEmbedding,
    ProductImage,
    ProductRow,
    ProductSource,
)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/m8"
PRIVATE = ROOT / "data/private/m8"
BASE = "http://127.0.0.1:8000/api/v1"


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8"
    )


def percentile(values, p):
    ordered = sorted(values)
    index = (len(ordered) - 1) * p
    lower = math.floor(index)
    return round(
        ordered[lower] + (ordered[math.ceil(index)] - ordered[lower]) * (index - lower),
        3,
    )


def timing(values):
    return {
        "p50_ms": percentile(values, 0.5),
        "p90_ms": percentile(values, 0.9),
        "p95_ms": percentile(values, 0.95),
        "p99_ms": percentile(values, 0.99),
    }


def prepare():
    sys.path.insert(0, str(ROOT))
    from data_pipeline.abo import BASE as SOURCE_BASE, IMAGE_LIMIT, download

    manifest = json.loads((PRIVATE / "validated.json").read_text(encoding="utf8"))
    metadata = {
        r["image_id"]: r
        for r in csv.DictReader(
            io.StringIO(
                gzip.decompress((PRIVATE / "images.csv.gz").read_bytes()).decode()
            )
        )
    }
    gallery_ids = {
        image["source_image_id"]
        for row in manifest["records"]
        for image in row["images"]
    }
    gallery_hashes = {
        image["source_sha256"] for row in manifest["records"] for image in row["images"]
    }
    selected = []
    counts = Counter()
    with httpx.Client(timeout=40, follow_redirects=False) as client:
        for row in manifest["records"]:
            if counts[row["group"]] >= 5:
                continue
            if row["category_id"] == "abo-op-dien-thoai":
                continue  # Explanatory line drawings occur among these alternate views.
            for image_id in row["raw"].get("other_image_id", [])[1:]:
                if image_id in gallery_ids or image_id not in metadata:
                    continue
                info = metadata[image_id]
                path = PRIVATE / "heldout" / info["path"]
                try:
                    raw = download(
                        client, "images/original/" + info["path"], path, IMAGE_LIMIT
                    )
                    digest = hashlib.sha256(raw).hexdigest()
                    if digest in gallery_hashes:
                        continue
                    with Image.open(io.BytesIO(raw)) as image:
                        if (
                            min(image.size) < 80
                            or image.width * image.height > 12_000_000
                        ):
                            continue
                        image.verify()
                    selected.append(
                        {
                            "product_id": row["id"],
                            "group": row["group"],
                            "category": row["category_id"],
                            "source_image_id": image_id,
                            "source_url": SOURCE_BASE
                            + "images/original/"
                            + info["path"],
                            "path": str(path.relative_to(PRIVATE)),
                            "sha256": digest,
                        }
                    )
                    counts[row["group"]] += 1
                    break
                except (ValueError, OSError, httpx.HTTPError):
                    continue
            if len(selected) == 20:
                break
    assert len(selected) == 20, (
        "Insufficient independent source photos; report actual count"
    )
    (PRIVATE / "heldout-selection.json").write_text(
        json.dumps(selected, indent=2), encoding="utf8"
    )
    sheet = Image.new("RGB", (1000, 4 * 240 + 45), "white")
    draw = ImageDraw.Draw(sheet)
    for n, row in enumerate(selected):
        with Image.open(PRIVATE / row["path"]) as image:
            image = image.convert("RGB")
            image.thumbnail((180, 190))
            x, y = (n % 5) * 200 + 10, (n // 5) * 240 + 5
            sheet.paste(image, (x, y))
            draw.text(
                (x, y + 195),
                f"{n + 1}. {row['group']}\n{row['product_id'][-10:]}",
                fill="black",
            )
    draw.text(
        (10, 970),
        "ABO images (c) Amazon.com | CC BY 4.0 | resized contact sheet; held-out source IDs",
        fill="black",
    )
    sheet.save(OUT / "heldout-contact.png")
    save(
        "image-qrels.json",
        {
            "source": "ABO CC-BY-4.0",
            "scope": "20 different source-photo IDs and original byte hashes, never indexed in gallery; same source product ID is the relevance label, no human population study",
            "queries": selected,
        },
    )
    print("Prepared 20 disjoint product-photo queries", flush=True)


async def audit():
    async with session_factory() as session:
        repository = SqlCatalogRepository(session, "real_demo")
        products, total = await repository.list_products(CatalogFilter(page_size=1000))
        rows = (
            await session.scalars(
                select(ProductImage).where(
                    ProductImage.product_id.in_([p.id for p in products])
                )
            )
        ).all()
        invalid = []
        for image in rows:
            path = CATALOG_MEDIA_ROOT / Path(image.storage_key).name
            if (
                not path.exists()
                or hashlib.sha256(path.read_bytes()).hexdigest() != image.sha256
            ):
                invalid.append(image.id)
            else:
                with Image.open(path) as content:
                    content.verify()
            thumbnail = path.with_name(path.stem + "-320.webp")
            if not thumbnail.exists():
                invalid.append(image.id + ":thumbnail")
        indexed = int(
            await session.scalar(
                select(func.count())
                .select_from(ImageEmbedding)
                .join(ProductImage, ProductImage.id == ImageEmbedding.image_id)
                .where(
                    ProductImage.product_id.in_([p.id for p in products]),
                    ImageEmbedding.model_revision == CLIP_REVISION,
                    ImageEmbedding.model_name == "OpenCLIP ViT-B/32",
                    ImageEmbedding.content_hash == ProductImage.sha256,
                )
            )
            or 0
        )
        stored = int(
            await session.scalar(
                select(func.count())
                .select_from(ProductRow)
                .where(ProductRow.data_profile == "real_demo")
            )
            or 0
        )
        categories = await repository.categories()
        result = {
            "stored_real_records": stored,
            "published_products": total,
            "photos": len(rows),
            "working_photos": len(rows) - len(invalid),
            "indexed_photos": indexed,
            "invalid": invalid,
            "categories_by_level": dict(Counter(c.level for c in categories)),
            "category_distribution": dict(Counter(p.category_name for p in products)),
            "missing_brand": sum(not p.brand for p in products),
            "missing_color": sum(p.color == "Chưa có thông tin" for p in products),
            "missing_material": sum(
                p.material == "Chưa có thông tin" for p in products
            ),
            "source_prices_available": 0,
            "merchant_stock_available": 0,
            "offer_scope": "Separate simulated offer and trial capacity, not source stock",
            "photo_bytes": sum(
                (CATALOG_MEDIA_ROOT / Path(image.storage_key).name).stat().st_size
                for image in rows
            ),
        }
        save("dataset-audit.json", result)
        assert not invalid and indexed == len(rows)
        sources = (
            await session.scalars(
                select(ProductSource).where(
                    ProductSource.product_id.in_([p.id for p in products])
                )
            )
        ).all()
        external_ids = {source.product_id: source.external_id for source in sources}
        save(
            "catalog-manifest.json",
            {
                "source": "Amazon Berkeley Objects / Amazon.com, CC-BY-4.0",
                "model_revision": CLIP_REVISION,
                "products": [
                    {
                        "id": product.id,
                        "slug": product.slug,
                        "name_vi": product.name_vi,
                        "category_id": product.category_id,
                        "source_id": product.source_id,
                        "external_id": external_ids[product.id],
                        "offer_scope": "separate simulated offer and trial capacity",
                        "images": [
                            {
                                "id": image.id,
                                "url": image.storage_key,
                                "thumbnail_url": image.storage_key.replace(
                                    ".webp", "-320.webp"
                                ),
                                "sha256": image.sha256,
                                "primary": image.is_primary,
                            }
                            for image in rows
                            if image.product_id == product.id
                        ],
                    }
                    for product in products
                ],
            },
        )
        captured = []

        def capture(conn, cursor, statement, parameters, context, executemany):
            if (
                context.compiled
                and statement.lstrip().startswith("SELECT")
                and "seller_offers" in statement
            ):
                captured.append(
                    str(
                        context.compiled.statement.compile(
                            dialect=conn.dialect, compile_kwargs={"literal_binds": True}
                        )
                    )
                )

        event.listen(engine.sync_engine, "before_cursor_execute", capture)
        try:
            await repository.list_products(CatalogFilter(page_size=24))
        finally:
            event.remove(engine.sync_engine, "before_cursor_execute", capture)
        plan = (
            await session.execute(
                text("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) " + captured[-1])
            )
        ).scalar_one()
        save("listing-explain.json", plan)
    await engine.dispose()
    print(json.dumps(result, indent=2, ensure_ascii=False), flush=True)


async def measure(cold=False):
    manifest = json.loads((PRIVATE / "validated.json").read_text(encoding="utf8"))
    selection = json.loads(
        (PRIVATE / "heldout-selection.json").read_text(encoding="utf8")
    )
    async with httpx.AsyncClient(base_url=BASE, timeout=65, trust_env=False) as client:
        catalog = (await client.get("/products", params={"page_size": 24})).json()
        count = catalog["total"]
        if cold:
            row = manifest["records"][0]
            raw = (CATALOG_MEDIA_ROOT / Path(row["images"][0]["url"]).name).read_bytes()
            started = time.perf_counter()
            response = await client.post(
                "/search/image", files={"image": ("cold.webp", raw, "image/webp")}
            )
            result = {
                "http_ms": round((time.perf_counter() - started) * 1000, 3),
                "status": response.status_code,
                "catalog_products": count,
                "scope": "First image search after explicit inference container restart; no parallel index/build",
                "response": response.json(),
            }
            save("image-cold.json", result)
            assert response.status_code == 200
            assert not result["response"]["media"]["cached"], (
                "Restart API as well as inference before a cold measurement"
            )
            return
        categories = {
            r["id"]: r["name_vi"] for r in (await client.get("/categories")).json()
        }
        groups = {}
        for row in manifest["records"]:
            groups.setdefault(row["category_id"], []).append(row)
        queries = []
        for category, rows in groups.items():
            name = categories[category]
            price = max(r["price_vnd"] for r in rows)
            plain = "".join(
                c
                for c in unicodedata.normalize("NFD", name.replace("đ", "d"))
                if not unicodedata.combining(c)
            )
            for query in [
                name,
                name.lower(),
                plain,
                f"tôi muốn mua {name}",
                f"{name} dưới {price + 1}",
                f"{name} không quá {price}",
            ]:
                queries.append(
                    {
                        "q": query,
                        "category": category,
                        "relevant_ids": [r["id"] for r in rows],
                    }
                )
        save(
            "text-qrels.json",
            {
                "scope": "Source/category-based structured oracle; six Vietnamese variants per category, not independent human semantic judgments",
                "queries": queries,
            },
        )
        text_groups = []
        for concurrency in [1, 5, 10]:
            semaphore = asyncio.Semaphore(concurrency)
            results = []

            async def one(row):
                async with semaphore:
                    started = time.perf_counter()
                    response = await client.get(
                        "/search/text", params={"q": row["q"], "page_size": 10}
                    )
                    elapsed = (time.perf_counter() - started) * 1000
                    response.raise_for_status()
                    data = response.json()
                    ids = [p["product"]["id"] for p in data["items"]]
                    relevant = set(row["relevant_ids"])
                    hits = [pid in relevant for pid in ids]
                    ideal = sum(
                        1 / math.log2(i + 2) for i in range(min(10, len(relevant)))
                    )
                    ndcg = (
                        sum(hit / math.log2(i + 2) for i, hit in enumerate(hits))
                        / ideal
                        if ideal
                        else 0
                    )
                    results.append(
                        {
                            "q": row["q"],
                            "tcp_ms": elapsed,
                            "service_ms": data["latency_ms"],
                            "ids": ids,
                            "precision_at_10": sum(hits) / 10,
                            "recall_at_10": sum(hits) / len(relevant),
                            "ndcg_at_10": ndcg,
                            "category_leaks": sum(
                                p["product"]["category_id"] != row["category"]
                                for p in data["items"]
                            ),
                        }
                    )

            await asyncio.gather(*(one(row) for row in queries))
            grids = []

            async def grid(n):
                async with semaphore:
                    started = time.perf_counter()
                    response = await client.get(
                        "/products",
                        params={
                            "page": n % max(1, math.ceil(count / 24)) + 1,
                            "page_size": 24,
                        },
                    )
                    response.raise_for_status()
                    grids.append((time.perf_counter() - started) * 1000)

            await asyncio.gather(*(grid(n) for n in range(60)))
            text_groups.append(
                {
                    "concurrency": concurrency,
                    "requests": len(results),
                    "tcp": timing([r["tcp_ms"] for r in results]),
                    "service": timing([r["service_ms"] for r in results]),
                    "grid_tcp": timing(grids),
                    "precision_at_10": statistics.mean(
                        r["precision_at_10"] for r in results
                    ),
                    "recall_at_10": statistics.mean(r["recall_at_10"] for r in results),
                    "ndcg_at_10": statistics.mean(r["ndcg_at_10"] for r in results),
                    "category_leaks": sum(r["category_leaks"] for r in results),
                    "results": results,
                }
            )
        save(
            "text-http.json",
            {
                "catalog_products": count,
                "scope": "Actual Windows HTTPX -> TCP -> Docker API -> PostgreSQL; no synthetic product clones; structured oracle only",
                "groups": text_groups,
            },
        )
        image_results = []
        # Warmup recorded separately; each measured query has distinct source bytes.
        warm = manifest["records"][0]
        warm_response = await client.post(
            "/search/image",
            files={
                "image": (
                    "warm.webp",
                    (
                        CATALOG_MEDIA_ROOT / Path(warm["images"][0]["url"]).name
                    ).read_bytes(),
                    "image/webp",
                )
            },
        )
        warm_response.raise_for_status()
        for row in selection:
            started = time.perf_counter()
            response = await client.post(
                "/search/image",
                files={
                    "image": (
                        "heldout.jpg",
                        (PRIVATE / row["path"]).read_bytes(),
                        "image/jpeg",
                    )
                },
                data={"page_size": "10"},
            )
            response.raise_for_status()
            data = response.json()
            ids = [p["product"]["id"] for p in data["items"]]
            image_results.append(
                {
                    **{k: v for k, v in row.items() if k != "path"},
                    "tcp_ms": round((time.perf_counter() - started) * 1000, 3),
                    "top10": ids,
                    "media": data["media"],
                    "stages_ms": data["stages_ms"],
                }
            )
        image_report = {
            "catalog_products": count,
            "queries_measured": len(image_results),
            "warm_http": timing([r["tcp_ms"] for r in image_results]),
            "scope": "20 held-out original source-photo IDs/bytes, source same-product-ID qrels. Warmup is a different catalog photo and excluded. Not a smartphone/human shopping study.",
            "recall": {
                str(k): statistics.mean(
                    r["product_id"] in r["top10"][:k] for r in image_results
                )
                for k in [1, 5, 10]
            },
            "ndcg_at_10": statistics.mean(
                1 / math.log2(r["top10"].index(r["product_id"]) + 2)
                if r["product_id"] in r["top10"]
                else 0
                for r in image_results
            ),
            "results": image_results,
        }
        save("image-http.json", image_report)
        assert all(not r["media"]["cached"] for r in image_results), (
            "Do not mix cached queries with fresh encoding"
        )
        assert all(g["category_leaks"] == 0 for g in text_groups)
        print(
            json.dumps(
                {k: v for k, v in image_report.items() if k != "results"}, indent=2
            ),
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "audit", "cold", "measure"])
    action = parser.parse_args().action
    if action == "prepare":
        prepare()
    else:
        asyncio.run(audit() if action == "audit" else measure(action == "cold"))
