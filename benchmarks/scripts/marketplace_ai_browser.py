"""Actual Chrome storefront/AI journeys, model and catalog unmocked."""

import json
import time
import uuid
import secrets
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

from m8_browser import settled

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/marketplace-ai"
BASE = "http://localhost:3000"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel="chrome", headless=True)
        for width in [360, 390, 768, 1280, 1440]:
            context = browser.new_context(viewport={"width": width, "height": 950})
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            response = page.goto(BASE, wait_until="networkidle")
            assert response.status == 200
            expect(page.locator(".product-card")).to_have_count(24)
            expect(page.locator("h1")).to_have_count(1)
            settled(page, scroll=True)
            page.screenshot(path=str(OUT / f"home-{width}.png"), full_page=True)
            if width == 1280:
                page.screenshot(path=str(OUT / "home-preview.png"))
            menu = page.get_by_role("button", name="Danh mục", exact=True)
            menu.click()
            expect(page.get_by_role("dialog")).to_be_visible()
            expect(
                page.get_by_role("heading", name="Danh mục sản phẩm", exact=True)
            ).to_be_visible()
            page.keyboard.press("Escape")
            expect(menu).to_be_focused()
            assert not errors
            results.append(
                {
                    "viewport": width,
                    "home_and_keyboard_menu": "passed",
                    "overflow": False,
                }
            )
            context.close()
        context = browser.new_context(viewport={"width": 1280, "height": 950})
        page = context.new_page()
        page.goto(BASE + "/assistant", wait_until="networkidle")
        page.get_by_role("button", name="Đèn bàn tối giản", exact=True).click()
        expect(page.get_by_label("Bạn muốn tìm món gì?", exact=True)).to_have_value(
            "Đèn bàn tối giản"
        )
        page.get_by_label("Bạn muốn tìm món gì?", exact=True).fill("chỗ ngồi")
        page.get_by_label("Giữ trong danh mục", exact=True).select_option("gia-dung")
        page.get_by_label("Ngân sách tối đa (₫)", exact=True).fill("3000000")
        with page.expect_response(
            lambda r: r.url.endswith("/search/describe") and r.request.method == "POST",
            timeout=65000,
        ) as event:
            page.get_by_role("button", name="Tìm lựa chọn phù hợp", exact=True).click()
        result = event.value.json()
        assert event.value.status == 200 and result["items"] and result["media"]
        assert all(r["product"]["price_vnd"] <= 3000000 for r in result["items"])
        expect(
            page.get_by_role("heading", name="Các lựa chọn dành cho bạn", exact=True)
        ).to_be_visible()
        settled(page, scroll=True)
        page.screenshot(path=str(OUT / "assistant-results-1280.png"), full_page=True)
        if result["total"] > 12:
            first_ids = {r["product"]["id"] for r in result["items"]}
            with page.expect_response(
                lambda r: r.url.endswith("/search/describe")
                and r.request.method == "POST"
            ) as event:
                page.get_by_role("button", name="Trang sau", exact=True).click()
            next_page = event.value.json()
            assert next_page["page"] == 2
            assert not first_ids.intersection(
                r["product"]["id"] for r in next_page["items"]
            )
        choices = page.locator(".compare-choice input")
        choices.nth(0).check()
        choices.nth(1).check()
        choices.nth(2).check()
        if choices.count() > 3:
            expect(choices.nth(3)).to_be_disabled()
        page.get_by_role("button", name="So sánh lựa chọn", exact=True).click()
        expect(
            page.get_by_role("heading", name="So sánh từ dữ liệu sản phẩm", exact=True)
        ).to_be_visible()
        expect(page.locator(".comparison-scroll thead th")).to_have_count(4)
        page.screenshot(path=str(OUT / "comparison-1280.png"), full_page=True)
        # Changing description keeps explicit UI constraints, without silently widening them.
        page.get_by_label("Bạn muốn tìm món gì?", exact=True).fill("đồ chiếu sáng")
        expect(page.get_by_label("Giữ trong danh mục", exact=True)).to_have_value(
            "gia-dung"
        )
        expect(page.get_by_label("Ngân sách tối đa (₫)", exact=True)).to_have_value(
            "3000000"
        )
        with page.expect_response(
            lambda r: r.url.endswith("/search/describe") and r.request.method == "POST",
            timeout=65000,
        ) as event:
            page.get_by_role("button", name="Tìm lựa chọn phù hợp", exact=True).click()
        assert event.value.status == 200
        # Unknown request actually reaches API and shows a recoverable error.
        page.get_by_label("Bạn muốn tìm món gì?", exact=True).fill("zzqqy không hiểu")
        with page.expect_response(
            lambda r: r.url.endswith("/search/describe") and r.request.method == "POST"
        ) as event:
            page.get_by_role("button", name="Tìm lựa chọn phù hợp", exact=True).click()
        assert event.value.status == 422
        expect(page.locator('.assistant-results [role="alert"]')).to_contain_text(
            "Chưa hiểu loại sản phẩm"
        )
        page.get_by_label("Cách tìm", exact=True).select_option("keyword")
        page.get_by_label("Giữ trong danh mục", exact=True).select_option("")
        page.get_by_label("Ngân sách tối đa (₫)", exact=True).fill("")
        page.get_by_label("Bạn muốn tìm món gì?", exact=True).fill("giày nam")
        with page.expect_response(
            lambda r: r.url.endswith("/search/describe") and r.request.method == "POST"
        ) as event:
            page.get_by_role("button", name="Tìm lựa chọn phù hợp", exact=True).click()
        assert event.value.status == 200 and event.value.json()["media"] is None
        results.append(
            {
                "actual_visual_search_budget_context_compare_pagination_unknown_keyword": "passed"
            }
        )
        page.set_viewport_size({"width": 390, "height": 950})
        settled(page, scroll=True)
        page.screenshot(path=str(OUT / "assistant-results-390.png"), full_page=True)
        page.goto(BASE + "/search/voice", wait_until="networkidle")
        page.get_by_label("Kiểm tra và sửa câu tìm kiếm", exact=True).fill("đèn bàn")
        page.get_by_role(
            "link", name="Tìm theo hình dáng từ câu đã sửa", exact=True
        ).click()
        expect(page.get_by_label("Bạn muốn tìm món gì?", exact=True)).to_have_value(
            "đèn bàn"
        )
        settled(page, scroll=True)
        results.append(
            {
                "mobile_ai_no_overflow_and_voice_correction_handoff": "passed",
                "scope": "Typed correction, not actual microphone/ASR acceptance",
            }
        )
        page.goto(BASE + "/auth/register", wait_until="networkidle")
        email = f"browser-ai-{uuid.uuid4().hex[:12]}@example.invalid"
        password = secrets.token_urlsafe(20)
        page.get_by_label("Email", exact=True).fill(email)
        page.get_by_label("Mật khẩu", exact=True).fill(password)
        page.get_by_role("button", name="Tạo tài khoản", exact=True).click()
        expect(page).to_have_url(BASE + "/account/orders", timeout=20000)
        page.get_by_role("link", name="Tài khoản", exact=True).click()
        page.locator("main").get_by_role("button", name="Đăng xuất", exact=True).click()
        expect(page).to_have_url(BASE + "/auth/login", timeout=15000)
        assert (context.request.get(BASE + "/api/v1/auth/me")).status == 401
        page.set_viewport_size({"width": 1280, "height": 950})
        page.get_by_label("Email", exact=True).fill(email)
        page.get_by_label("Mật khẩu", exact=True).fill(password)
        page.locator("main").get_by_role("button", name="Đăng nhập", exact=True).click()
        expect(page.locator(".utility-bar .header-logout")).to_be_visible(timeout=15000)
        assert page.locator('.utility-bar a[href="/manage"]').count() == 0
        page.locator(".utility-bar .header-logout").click()
        expect(page.locator('.utility-bar a[href="/auth/login"]')).to_be_visible(
            timeout=15000
        )
        assert page.locator(".utility-bar .header-logout").count() == 0
        assert (context.request.get(BASE + "/api/v1/auth/me")).status == 401
        results.append({"actual_registration_header_roles_logout_session": "passed"})
        browser.close()
    report = {
        "result": "passed",
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "results": results,
    }
    (OUT / "browser.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
