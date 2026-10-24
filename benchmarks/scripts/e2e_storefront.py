"""Real headless Chrome M2 journeys and responsive screenshots; no mocked catalog."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs/evidence/ui"
OUTPUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    context = browser.new_context(viewport={"width": 1440, "height": 1000})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto("http://localhost:3000", wait_until="networkidle")
    print(
        json.dumps(
            {
                "title": page.title(),
                "headings": page.locator("h1,h2").all_text_contents(),
                "buttons": page.get_by_role("button").all_text_contents(),
            },
            ensure_ascii=False,
        )
    )
    expect(page.locator(".product-card")).to_have_count(8)
    page.screenshot(path=str(OUTPUT / "home-desktop.png"), full_page=True)
    page.goto(
        "http://localhost:3000/products?category=ao-len-nam&color=%C4%91en&price_max=499999&sort=price_asc",
        wait_until="networkidle",
    )
    expect(page.locator(".product-card")).to_have_count(10)
    expect(page.locator(".product-card").first).to_contain_text("264.000")
    page.locator(".product-card h3 a").first.click()
    page.wait_for_load_state("networkidle")
    expect(
        page.get_by_role("heading", name="Áo len nam cổ tròn dệt kim")
    ).to_be_visible()
    page.get_by_role("button", name="Thêm vào giỏ hàng", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Đã thêm")
    page.get_by_role("link", name="Giỏ hàng, 1 sản phẩm").click()
    expect(page.locator(".cart-line")).to_have_count(1)
    page.get_by_role("button", name="Tăng số lượng").click()
    expect(page.locator(".order-summary")).to_contain_text("528.000")
    page.reload(wait_until="networkidle")
    expect(page.get_by_label("Số lượng", exact=True)).to_have_text("2")
    page.get_by_role("button", name="Xóa", exact=True).click()
    expect(page.get_by_role("heading", name="Giỏ hàng đang trống")).to_be_visible()
    for width in [360, 768]:
        page.set_viewport_size({"width": width, "height": 900})
        page.goto("http://localhost:3000", wait_until="networkidle")
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(path=str(OUTPUT / f"home-{width}.png"), full_page=True)
    response = page.goto(
        "http://localhost:3000/products/does-not-exist", wait_until="networkidle"
    )
    assert response and response.status == 404
    assert errors == [], errors
    (OUTPUT / "m2-results.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "journeys": [
                    "server-driven catalog",
                    "10 filtered sweaters",
                    "detail",
                    "add cart",
                    "quantity",
                    "cookie persistence",
                    "remove",
                    "360/768/1440 layout",
                    "real 404",
                ],
                "page_errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    browser.close()
