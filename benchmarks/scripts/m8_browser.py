"""Real Chrome M8 journeys. No mock catalog or ASR result; no TC2 pass claim."""

import json
import secrets
import subprocess
import sys
import time
import uuid
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/m8"
BASE = "http://localhost:3000"
OBSERVE = """(() => {
 window.__m8={lcp:0,cls:0,events:[]};
 new PerformanceObserver(l=>{for(const e of l.getEntries())window.__m8.lcp=e.startTime;}).observe({type:'largest-contentful-paint',buffered:true});
 new PerformanceObserver(l=>{for(const e of l.getEntries())if(!e.hadRecentInput)window.__m8.cls+=e.value;}).observe({type:'layout-shift',buffered:true});
 new PerformanceObserver(l=>{for(const e of l.getEntries())if(e.interactionId)window.__m8.events.push({name:e.name,duration:e.duration,id:e.interactionId});}).observe({type:'event',buffered:true,durationThreshold:16});
})()"""


def settled(page, scroll=False):
    page.wait_for_load_state("networkidle")
    if scroll:
        height = page.evaluate("document.documentElement.scrollHeight")
        for y in range(0, height, 700):
            page.evaluate("y=>scrollTo(0,y)", y)
            page.wait_for_timeout(70)
        page.wait_for_function(
            "[...document.images].every(i=>!i.getClientRects().length||(i.complete&&i.naturalWidth>0))"
        )
        page.evaluate("scrollTo(0,0)")
    assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), (
        "Horizontal overflow"
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    measurements = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        for width in [360, 390, 768, 1280, 1440]:
            context = browser.new_context(viewport={"width": width, "height": 950})
            context.add_init_script(OBSERVE)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            response = page.goto(BASE, wait_until="networkidle")
            assert response.status == 200
            expect(page.locator(".product-card")).to_have_count(24)
            expect(
                page.get_by_role(
                    "heading",
                    name=__import__("re").compile("Gợi ý khám phá|Khám phá sản phẩm"),
                )
            ).to_be_visible()
            search = page.get_by_label("Tìm nhanh sản phẩm", exact=True)
            search.fill("Giày")
            expect(page.locator("datalist option").first).to_have_attribute(
                "value", __import__("re").compile(".+")
            )
            search.focus()
            page.keyboard.press("Tab")
            assert page.evaluate("document.activeElement.tagName") in {"A", "BUTTON"}
            settled(page, scroll=True)
            assert page.locator(".photo-unavailable").count() == 0
            measurement = page.evaluate("window.__m8")
            measurement["width"] = width
            measurement["inp_candidate_ms"] = max(
                (e["duration"] for e in measurement["events"]), default=None
            )
            measurement["scope"] = (
                "Single local Chrome lab navigation and short real typing/focus journey; no throttling, not field INP"
            )
            measurements.append(measurement)
            page.screenshot(path=str(OUT / f"home-{width}.png"))
            page.screenshot(path=str(OUT / f"home-{width}-full.png"), full_page=True)
            page.goto(BASE + "/products", wait_until="networkidle")
            if width <= 768:
                page.get_by_role("button", name="Bộ lọc sản phẩm", exact=True).click()
                panel = page.get_by_role("dialog")
                expect(
                    panel.get_by_role("heading", name="Bộ lọc sản phẩm")
                ).to_be_visible()
            else:
                panel = page.locator(".desktop-filters")
            panel.get_by_label("Danh mục", exact=True).select_option("dien-tu")
            panel.get_by_role("button", name="Áp dụng bộ lọc", exact=True).click()
            expect(page).to_have_url(__import__("re").compile("category=dien-tu"))
            page.wait_for_load_state("networkidle")
            page.locator(".catalog-toolbar").get_by_role(
                "link", name="Giá tăng dần", exact=True
            ).click()
            expect(page).to_have_url(__import__("re").compile("sort=price_asc"))
            settled(page, scroll=True)
            page.screenshot(path=str(OUT / f"products-{width}.png"), full_page=True)
            page.get_by_role("link", name="Trang sau", exact=True).click()
            expect(page).to_have_url(__import__("re").compile("page=2"))
            settled(page)
            assert not errors, errors
            results.append(
                {
                    "width": width,
                    "home": "passed",
                    "suggestions_keyboard": "passed",
                    "filter_sort_pagination": "passed",
                    "overflow": False,
                    "page_errors": errors,
                }
            )
            context.close()
            print(f"Responsive {width}: passed", flush=True)

        context = browser.new_context(viewport={"width": 390, "height": 950})
        page = context.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        product = httpx.get(
            "http://127.0.0.1:8000/api/v1/products", params={"category": "abo-tai-nghe"}
        ).json()["items"][0]
        page.goto(BASE + "/products/" + product["slug"], wait_until="networkidle")
        expect(
            page.get_by_role("heading", name=product["name_vi"], exact=True)
        ).to_be_visible()
        if page.get_by_role("button", name="Xem ảnh 2", exact=True).count():
            page.get_by_role("button", name="Xem ảnh 2", exact=True).click()
            expect(
                page.get_by_role("button", name="Xem ảnh 2", exact=True)
            ).to_have_attribute("aria-pressed", "true")
        page.get_by_role("button", name="Phóng to ảnh sản phẩm", exact=True).click()
        expect(page.get_by_role("dialog")).to_be_visible()
        page.keyboard.press("Escape")
        expect(page.get_by_role("dialog")).not_to_be_visible()
        settled(page, scroll=True)
        page.screenshot(path=str(OUT / "detail-390.png"), full_page=True)
        page.get_by_role("button", name="Thêm vào giỏ hàng", exact=True).click()
        expect(page.get_by_role("status")).to_contain_text("Đã thêm")
        page.goto(BASE + "/cart", wait_until="networkidle")
        expect(page.locator(".cart-line h2")).to_contain_text(product["name_vi"])
        page.get_by_role(
            "button", name="Tăng số lượng " + product["name_vi"], exact=True
        ).click()
        expect(page.get_by_label("Số lượng", exact=True)).to_have_text("2")
        page.get_by_role(
            "button", name="Giảm số lượng " + product["name_vi"], exact=True
        ).click()
        expect(page.get_by_label("Số lượng", exact=True)).to_have_text("1")
        page.get_by_role("button", name="Xóa", exact=True).click()
        expect(
            page.get_by_role("heading", name="Giỏ hàng đang trống", exact=True)
        ).to_be_visible()
        page.goto(BASE + "/products/" + product["slug"], wait_until="networkidle")
        page.get_by_role("button", name="Đặt thử ngay", exact=True).click()
        expect(page).to_have_url(BASE + "/cart")
        page.goto(BASE + "/auth/register?next=/cart", wait_until="networkidle")
        email = "m8-browser-" + uuid.uuid4().hex[:10] + "@example.invalid"
        password = secrets.token_urlsafe(20)
        page.get_by_label("Email", exact=True).fill(email)
        page.get_by_label("Mật khẩu", exact=True).fill(password)
        page.get_by_role("button", name="Tạo tài khoản", exact=True).click()
        expect(page).to_have_url(BASE + "/cart", timeout=20000)
        expect(page.locator(".cart-line")).to_have_count(1)
        page.get_by_role("button", name="Đặt đơn mô phỏng", exact=True).click()
        page.get_by_label("Người nhận", exact=True).fill("Kiểm thử M8")
        page.get_by_label("Số điện thoại", exact=True).fill("0900000000")
        page.get_by_label("Địa chỉ", exact=True).fill(
            "Địa chỉ mô phỏng phục vụ kiểm thử"
        )
        settled(page)
        page.screenshot(path=str(OUT / "checkout-390.png"), full_page=True)
        page.get_by_role("button", name="Xác nhận đặt đơn mô phỏng", exact=True).click()
        expect(page).to_have_url(
            __import__("re").compile("/account/orders/HM"), timeout=20000
        )
        code = page.url.rsplit("/", 1)[-1]
        expect(page.locator(".order-card")).to_contain_text("Đã xác nhận")
        page.screenshot(path=str(OUT / "order-390.png"), full_page=True)
        # Separate anonymous browser cannot read order. Never print session cookies.
        outsider = browser.new_context()
        forbidden = outsider.request.get(BASE + "/api/v1/orders/" + code)
        assert forbidden.status == 401
        csrf = outsider.request.get(BASE + "/api/v1/auth/csrf").json()["token"]
        registered = outsider.request.post(
            BASE + "/api/v1/auth/register",
            data={
                "email": "m8-other-" + uuid.uuid4().hex[:10] + "@example.invalid",
                "password": secrets.token_urlsafe(20),
            },
            headers={"Origin": BASE, "X-CSRF-Token": csrf},
        )
        assert registered.status in {200, 201}
        assert outsider.request.get(BASE + "/api/v1/orders/" + code).status == 404
        outsider.close()
        page.get_by_role("button", name="Hủy đơn mô phỏng", exact=True).click()
        expect(page.locator(".order-card")).to_contain_text("Đã hủy", timeout=20000)
        current = httpx.get(
            "http://127.0.0.1:8000/api/v1/products/" + product["id"]
        ).json()
        assert current["available_quantity"] == product["available_quantity"]
        results.append(
            {
                "gallery_zoom_cart_qty_remove_buy_now": "passed",
                "real_registration_mock_checkout_owner_cancel": "passed",
                "stock_restored": True,
                "anonymous_order": 401,
                "other_user_order": 404,
                "cancelled_test_order": code,
            }
        )

        page.goto(BASE + "/search/voice", wait_until="networkidle")
        page.get_by_placeholder(
            "Bạn cũng có thể nhập trực tiếp tại đây", exact=True
        ).fill("tai nghe")
        page.get_by_role("button", name="Tìm bằng câu đã sửa", exact=True).click()
        expect(page).to_have_url(__import__("re").compile("modality=voice"))
        settled(page)
        expect(page.locator(".product-card").first).to_be_visible()
        page.goto(BASE + "/search/image", wait_until="networkidle")
        selection = json.loads(
            (ROOT / "data/private/m8/heldout-selection.json").read_text(encoding="utf8")
        )
        photo = ROOT / "data/private/m8" / selection[0]["path"]
        page.get_by_label("Ảnh sản phẩm", exact=True).set_input_files(str(photo))
        page.get_by_role("button", name="Tìm sản phẩm tương tự", exact=True).click()
        expect(page.locator(".product-card").first).to_be_visible(timeout=60000)
        settled(page, scroll=True)
        page.screenshot(path=str(OUT / "image-search-390.png"), full_page=True)
        # Corrupt file: actual backend rejection; then meaningful empty state and 404.
        page.get_by_label("Ảnh sản phẩm", exact=True).set_input_files(
            {"name": "bad.jpg", "mimeType": "image/jpeg", "buffer": b"not an image"}
        )
        page.get_by_role("button", name="Tìm sản phẩm tương tự", exact=True).click()
        expect(page.get_by_role("alert")).to_be_visible(timeout=15000)
        page.goto(BASE + "/products?price_max=1", wait_until="networkidle")
        expect(
            page.get_by_role("heading", name="Chưa có sản phẩm phù hợp", exact=True)
        ).to_be_visible()
        missing = context.request.get(BASE + "/products/definitely-missing-m8")
        assert missing.status == 404
        assert not errors, errors
        results.append(
            {
                "editable_voice_common_search": "passed, typed correction only; not TC2 audio",
                "real_image_upload_results_and_invalid_upload": "passed",
                "empty_and_missing_product": "passed",
                "page_errors": errors,
            }
        )
        staff = browser.new_context(viewport={"width": 1440, "height": 950})
        csrf = staff.request.get(BASE + "/api/v1/auth/csrf").json()["token"]
        registered = staff.request.post(
            BASE + "/api/v1/auth/register",
            data={
                "email": "browser-m8-readonly-"
                + uuid.uuid4().hex[:10]
                + "@example.invalid",
                "password": secrets.token_urlsafe(20),
            },
            headers={"Origin": BASE, "X-CSRF-Token": csrf},
        )
        assert registered.status in {200, 201}
        actor = staff.request.get(BASE + "/api/v1/auth/me").json()
        operator = ROOT / "benchmarks/scripts/fixture_owner.py"
        subprocess.run(
            [sys.executable, str(operator), actor["id"], "grant-admin"],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        try:
            managed = staff.new_page()
            managed.goto(BASE + "/manage", wait_until="networkidle")
            expect(
                managed.get_by_text(
                    "Danh mục ảnh thật được cập nhật qua đợt nhập có kiểm duyệt. Tạo, sửa và duyệt bằng biểu mẫu chưa được hỗ trợ ở chế độ này.",
                    exact=True,
                )
            ).to_be_visible()
            assert managed.locator(".manage-create").count() == 0
            assert managed.locator(".managed-list .order-card").count() > 0
            managed.screenshot(
                path=str(OUT / "management-readonly.png"), full_page=True
            )
            results.append(
                {
                    "management_real_catalog_explicit_read_only": "passed",
                    "temporary_test_role_revoked": True,
                }
            )
        finally:
            subprocess.run(
                [sys.executable, str(operator), actor["id"], "revoke-admin"],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            staff.close()
        context.close()
        browser.close()
    (OUT / "browser.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "results": results,
                "measurements": measurements,
                "scope": "Actual Chrome/Docker/DB flows; typed voice correction is not actual TC2 ASR",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf8",
    )
    print("M8 browser journeys passed", flush=True)


if __name__ == "__main__":
    started = time.perf_counter()
    main()
    print(f"Elapsed {time.perf_counter() - started:.3f}s", flush=True)
