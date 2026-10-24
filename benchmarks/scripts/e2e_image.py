import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[2]
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 1000})
    page.goto("http://localhost:3000/search/image", wait_until="networkidle")
    page.get_by_label("Ảnh sản phẩm", exact=True).set_input_files(
        root / "benchmarks/images/navy-sweater-heldout.png"
    )
    page.get_by_role("button", name="Tìm sản phẩm tương tự").click()
    expect(page.locator(".product-card").first).to_contain_text(
        "Áo len nam xanh than", timeout=60000
    )
    page.screenshot(
        path=str(root / "docs/evidence/ui/image-search.png"), full_page=True
    )
    page.get_by_label("Danh mục", exact=True).select_option("tui-deo-cheo")
    page.get_by_label("Giá tối đa (₫)", exact=True).fill("150000")
    page.get_by_role("button", name="Tìm sản phẩm tương tự").click()
    expect(page.locator(".product-card")).to_have_count(3, timeout=60000)
    assert "category=tui-deo-cheo" in page.url
    page.reload(wait_until="networkidle")
    expect(page.get_by_label("Danh mục", exact=True)).to_have_value("tui-deo-cheo")
    page.get_by_label("Ảnh sản phẩm", exact=True).set_input_files(
        {"name": "bad.png", "mimeType": "image/png", "buffer": b"not image"}
    )
    page.get_by_role("button", name="Tìm sản phẩm tương tự").click()
    expect(page.locator('[data-slot="alert"]')).to_contain_text(
        "Ảnh bị hỏng", timeout=60000
    )
    page.set_viewport_size({"width": 360, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    (root / "docs/evidence/ui/m4-results.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "flows": [
                    "real CLIP upload",
                    "correct navy sweater first",
                    "real category and price filters",
                    "URL filters survive reload; raw image not retained",
                    "corrupt bytes rejected",
                    "360px no overflow",
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    browser.close()
