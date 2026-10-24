"""Measure real catalog HTTP latency only; no search/model performance claims."""

import argparse
import asyncio
import json
import math
import os
import platform
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx


def percentile(samples: list[float], p: float) -> float:
    return round(sorted(samples)[max(0, math.ceil(len(samples) * p) - 1)], 3)


async def benchmark(base_url: str, count: int) -> dict[str, object]:
    results: list[dict[str, object]] = []
    async with httpx.AsyncClient(
        base_url=base_url, timeout=10, trust_env=False
    ) as client:
        first_start = time.perf_counter()
        first = await client.get("/api/v1/products")
        first.raise_for_status()
        first_ms = (time.perf_counter() - first_start) * 1000
        for concurrency in [1, 5, 10]:
            semaphore = asyncio.Semaphore(concurrency)

            async def request(index: int) -> float:
                async with semaphore:
                    started = time.perf_counter()
                    response = await client.get(
                        "/api/v1/products",
                        params={
                            "category": "thoi-trang-nam" if index % 2 else "phu-kien",
                            "page_size": 12,
                            "sort": "price_asc",
                        },
                    )
                    response.raise_for_status()
                    assert "items" in response.json()
                    return (time.perf_counter() - started) * 1000

            # Establish pool/query caches. Samples exclude queue wait before the semaphore.
            await asyncio.gather(*(request(i) for i in range(10)))
            started = time.perf_counter()
            samples = await asyncio.gather(*(request(i) for i in range(count)))
            results.append(
                dict(
                    concurrency=concurrency,
                    count=count,
                    successes=len(samples),
                    p50_ms=percentile(samples, 0.50),
                    p90_ms=percentile(samples, 0.90),
                    p95_ms=percentile(samples, 0.95),
                    p99_ms=percentile(samples, 0.99),
                    total_wall_ms=round((time.perf_counter() - started) * 1000, 3),
                )
            )
    return dict(
        measured_at=datetime.now(UTC).isoformat(),
        platform=platform.platform(),
        processor=platform.processor(),
        logical_cpus=os.cpu_count(),
        client_python=platform.python_version(),
        fixture="2026-10-21-v1",
        stored_products=55,
        visible_products=50,
        endpoint="GET /api/v1/products",
        first_probe_ms=round(first_ms, 3),
        scope="Client HTTP round-trip from Windows to Docker API, warm DB; not 3k/search/model SLO",
        runs=results,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--count", type=int, default=100)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/evidence/catalog-benchmark.json")
    )
    args = parser.parse_args()
    if args.count < 10 or args.count > 10000:
        parser.error("count must be 10..10000")
    result = asyncio.run(benchmark(args.base_url, args.count))
    rendered = json.dumps(result, indent=2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
