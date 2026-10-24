import asyncio
import json
import math
import platform
import time
from pathlib import Path
import httpx


async def main():
    queries = [
        "áo len nam màu đen dưới 500k",
        "ao len nam den duoi 500 nghin",
        "túi đeo chéo đỏ dưới 150k",
        "tôi muốn mua áo mùa đông",
        "mèo bay ngoài hành tinh",
    ]
    runs = []
    async with httpx.AsyncClient(
        base_url="http://localhost:8000", timeout=15, trust_env=False
    ) as client:
        for concurrency in [1, 5, 10]:
            lock = asyncio.Semaphore(concurrency)

            async def request(i):
                async with lock:
                    t = time.perf_counter()
                    r = await client.post(
                        "/api/v1/search/text", json={"q": queries[i % len(queries)]}
                    )
                    r.raise_for_status()
                    return (time.perf_counter() - t) * 1000, r.json()["latency_ms"]

            await asyncio.gather(*(request(i) for i in range(10)))
            results = await asyncio.gather(*(request(i) for i in range(100)))

            def pct(values, p):
                return round(sorted(values)[math.ceil(len(values) * p) - 1], 3)

            runs.append(
                {
                    "concurrency": concurrency,
                    "success": len(results),
                    "http_ms": {
                        f"p{n}": pct([r[0] for r in results], n / 100)
                        for n in [50, 90, 95, 99]
                    },
                    "service_ms": {
                        f"p{n}": pct([r[1] for r in results], n / 100)
                        for n in [50, 90, 95, 99]
                    },
                }
            )
    result = {
        "platform": platform.platform(),
        "scope": "55 original stored fixture products; 5 queries; warm only; no hybrid model",
        "runs": runs,
    }
    Path("docs/evidence/text-benchmark.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
