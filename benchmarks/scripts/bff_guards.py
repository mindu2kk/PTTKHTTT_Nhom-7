"""Actual loopback HTTP chunked/slow-body negative tests at the frontend boundary."""

import asyncio
import json
import time
from pathlib import Path
from urllib.parse import quote

import httpx

ROOT = Path(__file__).resolve().parents[2]


async def request(path: str, content_type: str, raw: bytes, finish: bool):
    reader, writer = await asyncio.open_connection("127.0.0.1", 3000)
    headers = (
        f"POST {path} HTTP/1.1\r\nHost: localhost:3000\r\nOrigin: http://localhost:3000\r\nContent-Type: {content_type}\r\nTransfer-Encoding: chunked\r\nConnection: close\r\n\r\n"
    ).encode()
    started = time.perf_counter()
    try:
        writer.write(
            headers
            + f"{len(raw):x}\r\n".encode()
            + raw
            + b"\r\n"
            + (b"0\r\n\r\n" if finish else b"")
        )
        await writer.drain()
        response = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=21)
        return {
            "path": path,
            "status": int(response.split(b" ")[1]),
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "finished_body": finish,
        }
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    malformed_carts = []
    async with httpx.AsyncClient(
        base_url="http://localhost:3000", follow_redirects=False, trust_env=False
    ) as client:
        for cart in [
            {},
            [{"id": "sweater-01", "quantity": -1}],
            [{"id": "sweater-01", "quantity": 100}],
            [{"id": "sweater-01", "quantity": 1}] * 2,
        ]:
            response = await client.post(
                "/cart/add",
                headers={
                    "Origin": "http://localhost:3000",
                    "Cookie": "hm_cart=" + quote(json.dumps(cart)),
                },
                data={"id": "sweater-01", "quantity": "1"},
            )
            assert response.status_code == 422, response.text
            malformed_carts.append(response.status_code)
        valid = await client.post(
            "/cart/add",
            headers={"Origin": "http://localhost:3000"},
            data={"id": "sweater-01", "quantity": "1"},
        )
        assert (
            valid.status_code == 303
            and valid.headers["location"] == "http://localhost:3000/cart"
        )
        assert "hm_cart" in valid.cookies
    large = await request(
        "/cart/add", "application/x-www-form-urlencoded", b"x" * 20000, True
    )
    assert large["status"] == 413, large
    stalled = await asyncio.gather(
        request("/api/v1/search/image", "application/octet-stream", b"test", False),
        request("/cart/add", "application/x-www-form-urlencoded", b"id=x", False),
    )
    assert all(
        row["status"] == 408 and row["elapsed_seconds"] < 20 for row in stalled
    ), stalled
    report = {
        "result": "passed",
        "protocol": "Actual raw HTTP/1.1 against Docker Next BFF; unterminated chunked bodies, no API mocks",
        "oversize": large,
        "invalid_guest_cart_shapes_quantities_duplicates": malformed_carts,
        "valid_no_javascript_cart": valid.status_code,
        "stalled": stalled,
    }
    (ROOT / "docs/evidence/bff-upload-guards.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
