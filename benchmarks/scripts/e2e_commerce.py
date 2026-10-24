import json
import secrets
import uuid
import atexit
import subprocess
import sys
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parents[2]
email = f"browser-{uuid.uuid4().hex}@example.invalid"
password = secrets.token_urlsafe(20)
product = httpx.get("http://127.0.0.1:8000/api/v1/products/sweater-01").json()
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 1000})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto("http://localhost:3000/auth/register", wait_until="networkidle")
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Mật khẩu", exact=True).fill(password)
    page.get_by_role("button", name="Tạo tài khoản").click()
    expect(page).to_have_url("http://localhost:3000/account/orders", timeout=20000)
    actor = context.request.get("http://localhost:3000/api/v1/auth/me").json()
    subprocess.run(
        [
            sys.executable,
            str(root / "benchmarks/scripts/fixture_owner.py"),
            actor["id"],
            "bind",
        ],
        check=True,
    )
    atexit.register(
        lambda: subprocess.run(
            [
                sys.executable,
                str(root / "benchmarks/scripts/fixture_owner.py"),
                actor["id"],
                "restore",
            ],
            check=True,
        )
    )
    session = next(c for c in context.cookies() if c["name"] == "hm_session")
    assert session["httpOnly"] and session["sameSite"] == "Lax"
    page.get_by_label("Cho phép lưu lịch sử tìm kiếm").check()
    expect(page.get_by_role("status")).to_contain_text("Đã bật")
    page.goto(
        "http://localhost:3000/search?q="
        + __import__("urllib.parse", fromlist=["quote"]).quote(
            "kiểm tra đơn hàng 20261005"
        ),
        wait_until="networkidle",
    )
    expect(page.get_by_role("heading", name="Kết quả tra cứu đơn hàng")).to_be_visible()
    expect(page.locator(".order-card")).to_contain_text("710.500")
    expect(page.locator(".order-card")).to_contain_text("115.500")
    expect(page.locator(".order-card")).to_contain_text("595.000")
    page.screenshot(
        path=str(root / "docs/evidence/ui/course-order.png"), full_page=True
    )
    page.goto(
        f"http://localhost:3000/products/{product['slug']}", wait_until="networkidle"
    )
    page.get_by_role("button", name="Thêm vào giỏ hàng").click()
    expect(page.get_by_role("status")).to_contain_text("Đã thêm")
    page.goto("http://localhost:3000/cart", wait_until="networkidle")
    page.get_by_role("button", name="Đặt đơn mô phỏng", exact=True).click()
    page.get_by_label("Người nhận", exact=True).fill("Khách kiểm thử")
    page.get_by_label("Số điện thoại", exact=True).fill("0900000000")
    page.get_by_label("Địa chỉ", exact=True).fill("Địa chỉ mô phỏng kiểm thử")
    page.locator("select[name=method]").select_option("mock")
    page.get_by_role("button", name="Xác nhận đặt đơn mô phỏng", exact=True).click()
    expect(page).to_have_url(
        __import__("re").compile(r"/account/orders/HM[A-F0-9]+$"), timeout=20000
    )
    code = page.url.rsplit("/", 1)[-1]
    expect(page.locator(".order-card")).to_contain_text("Đã xác nhận")
    page.screenshot(
        path=str(root / "docs/evidence/ui/order-desktop.png"), full_page=True
    )
    page.goto(
        "http://localhost:3000/search?q="
        + __import__("urllib.parse", fromlist=["quote"]).quote(
            "kiểm tra đơn hàng " + code
        ),
        wait_until="networkidle",
    )
    expect(page.get_by_role("heading", name="Kết quả tra cứu đơn hàng")).to_be_visible()
    expect(page.locator(".order-card")).to_contain_text(code)
    private = browser.new_context()
    other = private.new_page()
    other.goto(f"http://localhost:3000/account/orders/{code}", wait_until="networkidle")
    expect(
        other.get_by_role("link", name="Đăng nhập để xem đơn hàng của bạn")
    ).to_be_visible()
    assert (
        private.request.get(f"http://localhost:3000/api/v1/orders/{code}").status == 401
    )
    private.close()
    page.goto(f"http://localhost:3000/account/orders/{code}", wait_until="networkidle")
    page.get_by_role("button", name="Hủy đơn mô phỏng").click()
    expect(page.locator(".order-card")).to_contain_text("Đã hủy")
    page.set_viewport_size({"width": 360, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(
        path=str(root / "docs/evidence/ui/order-mobile.png"), full_page=True
    )
    page.goto(
        "http://localhost:3000/search?q="
        + __import__("urllib.parse", fromlist=["quote"]).quote("áo len nam"),
        wait_until="networkidle",
    )
    page.goto("http://localhost:3000/account/history", wait_until="networkidle")
    expect(page.get_by_role("link", name="áo len nam", exact=True)).to_be_visible()
    page.goto("http://localhost:3000/account/orders", wait_until="networkidle")
    page.get_by_role("button", name="Xóa lịch sử", exact=True).click()
    expect(page.get_by_role("status")).to_contain_text("Đã xóa")
    page.get_by_role("button", name="Đăng xuất", exact=True).click()
    expect(page.get_by_role("heading", name="Đăng nhập", exact=True)).to_be_visible()
    # Local operator setup for this harness account only; revoked on process exit.
    subprocess.run(
        [
            sys.executable,
            str(root / "benchmarks/scripts/fixture_owner.py"),
            actor["id"],
            "grant-admin",
        ],
        check=True,
    )
    atexit.register(
        lambda: subprocess.run(
            [
                sys.executable,
                str(root / "benchmarks/scripts/fixture_owner.py"),
                actor["id"],
                "revoke-admin",
            ],
            check=True,
        )
    )
    page.get_by_label("Email", exact=True).fill(email)
    page.get_by_label("Mật khẩu", exact=True).fill(password)
    page.get_by_role("button", name="Đăng nhập", exact=True).click()
    expect(page).to_have_url("http://localhost:3000/account/orders", timeout=20000)
    page.goto("http://localhost:3000/manage", wait_until="networkidle")
    page.get_by_text("Tạo sản phẩm mô phỏng", exact=True).click()
    name = "Áo len mô phỏng kiểm thử " + uuid.uuid4().hex[:8]
    create = page.locator(".manage-create").first
    create.get_by_label("Tên sản phẩm", exact=True).fill(name)
    create.get_by_label("Mô tả", exact=True).fill(
        "Dữ liệu nguyên bản mô phỏng phục vụ kiểm thử giao diện"
    )
    create.locator("select[name=category]").select_option("ao-len-nam")
    create.locator("select[name=image]").select_option("image-catalog-01")
    create.get_by_label("Giá (₫)", exact=True).fill("250000")
    create.get_by_label("Tồn kho", exact=True).fill("3")
    create.get_by_label("Màu", exact=True).fill("đen")
    create.get_by_label("Chất liệu", exact=True).fill("len")
    create.get_by_role("checkbox").check()
    create.get_by_role("button", name="Lưu bản nháp", exact=True).click()
    row = page.locator(".managed-list .order-card").filter(has_text=name)
    expect(row).to_contain_text("Bản nháp", timeout=20000)
    row.get_by_role("button", name="Duyệt và xuất bản", exact=True).click()
    expect(row).to_contain_text("Đã xuất bản", timeout=20000)
    row.get_by_role("button", name="Lưu trữ", exact=True).click()
    expect(row).to_contain_text("Đã lưu trữ", timeout=20000)
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.screenshot(
        path=str(root / "docs/evidence/ui/admin-reviewed.png"), full_page=True
    )
    assert not errors, errors
    (root / "docs/evidence/ui/m6-results.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "created_cancelled_demo_order": code,
                "flows": [
                    "real registration and HttpOnly session",
                    "real API checkout, fresh prices",
                    "owner universal order intent",
                    "anonymous denied order",
                    "cancel releases stock",
                    "history opt-in/search/delete",
                    "logout",
                    "canonical TC5 owner 20261005",
                    "real login and operator-scoped admin draft/publish/archive UI",
                    "360px no overflow",
                ],
                "page_errors": errors,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf8",
    )
    browser.close()
