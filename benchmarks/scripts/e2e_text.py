"""TC1, TC4 with explicit expansion consent, UI filters and empty state in real Chrome."""

import json
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

out = Path(__file__).resolve().parents[2] / "docs/evidence/ui"
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto("http://localhost:3000", wait_until="networkidle")
    page.get_by_label("Bạn đang tìm gì?", exact=True).fill(
        "áo len nam màu đen dưới 500k"
    )
    page.get_by_role("button", name="Tìm kiếm", exact=True).click()
    page.wait_for_load_state("networkidle")
    expect(page.locator(".product-card")).to_have_count(10)
    expect(page.locator(".product-card").first).to_contain_text("264.000")
    expect(page.locator(".interpreted-filters")).to_contain_text("Dưới 500.000")
    page.screenshot(path=str(out / "text-tc1.png"), full_page=True)
    page.goto(
        "http://localhost:3000/search?q=túi đeo chéo màu đỏ dưới 150k",
        wait_until="networkidle",
    )
    expect(page.locator(".product-card")).to_have_count(1)
    page.get_by_role("link", name="Cho phép mở rộng màu").click()
    expect(page.locator(".product-card")).to_have_count(3)
    expect(page.locator(".product-card").first).to_contain_text("95.000")
    expect(page.locator(".product-grid")).to_contain_text("99.000")
    expect(page.locator(".product-grid")).to_contain_text("149.000")
    expect(page.locator(".interpreted-filters")).to_contain_text("đã nới")
    page.screenshot(path=str(out / "text-tc4-consent.png"), full_page=True)
    page.goto(
        "http://localhost:3000/search?q=mèo bay ngoài hành tinh",
        wait_until="networkidle",
    )
    expect(page.get_by_role("heading", name="Chưa có sản phẩm phù hợp")).to_be_visible()
    page.goto(
        "http://localhost:3000/search?q=kiểm tra đơn hàng 20261005",
        wait_until="networkidle",
    )
    expect(
        page.get_by_role("heading", name="Tra cứu đơn hàng", exact=True)
    ).to_be_visible()
    expect(page.locator("body")).not_to_contain_text("710.500")
    (out / "m3-results.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "tests": [
                    "TC1 actual text flow",
                    "TC4 strict plus consent expansion",
                    "unrelated empty",
                    "order intent requires login",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    browser.close()
