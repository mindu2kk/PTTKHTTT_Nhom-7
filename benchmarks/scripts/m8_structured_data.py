"""Check actual M8 product JSON-LD and visible trial controls after final build."""

import json
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/m8"


def main():
    manifest = json.loads((OUT / "catalog-manifest.json").read_text(encoding="utf8"))
    slug = manifest["products"][0]["slug"]
    response = httpx.get(f"http://localhost:8000/api/v1/products/{slug}")
    response.raise_for_status()
    product = response.json()
    assert product["data_profile"] == "real_demo"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 390, "height": 950})
        response = page.goto(
            f"http://localhost:3000/products/{slug}", wait_until="networkidle"
        )
        assert response.status == 200
        data = json.loads(
            page.locator('script[type="application/ld+json"]').inner_text()
        )
        assert data["@type"] == "Product" and data["sku"] == product["id"]
        assert "offers" not in data
        assert data["additionalProperty"] == [
            {
                "@type": "PropertyValue",
                "name": "Giá đặt thử mô phỏng",
                "value": product["price_vnd"],
                "unitText": "VND",
            }
        ]
        expect(page.locator(".detail-price")).to_be_visible()
        expect(page.get_by_label("Số lượng", exact=True)).to_be_enabled()
        expect(
            page.get_by_role("button", name="Thêm vào giỏ hàng", exact=True)
        ).to_be_enabled()
        missing = page.goto("http://localhost:3000/products/m8-missing-final-check")
        assert missing.status == 404
        browser.close()
    (OUT / "structured-data.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "slug": slug,
                "product_json_ld": data,
                "trial_controls_visible": True,
                "missing_product_http": 404,
                "scope": "Actual Chrome after final build; demo price is not a merchant Offer",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    print("M8 structured data, trial controls and HTTP 404 passed")


if __name__ == "__main__":
    main()
