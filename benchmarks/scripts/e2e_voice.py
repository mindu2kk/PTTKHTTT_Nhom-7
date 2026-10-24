import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

root = Path(__file__).resolve().parents[2]
with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chrome", headless=True, args=["--deny-permission-prompts"]
    )
    page = browser.new_page(viewport={"width": 1280, "height": 1000})
    page.goto("http://localhost:3000/search/voice", wait_until="networkidle")
    page.get_by_role("button", name="Bắt đầu ghi âm").click()
    expect(page.locator(".voice-panel [role=alert]")).to_contain_text(
        "Chưa được cấp quyền micro", timeout=15000
    )
    page.get_by_label("Tệp âm thanh", exact=True).set_input_files(
        root / "benchmarks/audio/course-tts.wav"
    )
    page.get_by_role("button", name="Chuyển thành chữ").click()
    expect(page.get_by_label("Kiểm tra và sửa câu tìm kiếm")).not_to_have_value(
        "", timeout=60000
    )
    hypothesis = page.get_by_label("Kiểm tra và sửa câu tìm kiếm").input_value()
    page.screenshot(
        path=str(root / "docs/evidence/ui/voice-transcript.png"), full_page=True
    )
    page.get_by_label("Kiểm tra và sửa câu tìm kiếm").fill("tôi muốn mua áo mùa đông")
    page.get_by_role("button", name="Tìm bằng câu đã sửa").click()
    expect(page.locator(".product-card").first).to_contain_text("Áo phao")
    expect(page.locator(".interpreted-filters")).to_contain_text("mùa đông")
    assert "modality=voice" in page.url
    page.goto("http://localhost:3000/search/voice", wait_until="networkidle")
    page.route(
        "**/api/v1/search/voice",
        lambda route: route.fulfill(
            status=503,
            content_type="application/json",
            body=json.dumps(
                {"detail": "Mô hình tạm thời chưa sẵn sàng. Hãy nhập văn bản."}
            ),
        ),
    )
    page.get_by_label("Tệp âm thanh", exact=True).set_input_files(
        root / "benchmarks/audio/course-tts.wav"
    )
    page.get_by_role("button", name="Chuyển thành chữ").click()
    expect(page.locator(".voice-panel [role=alert]")).to_contain_text(
        "Hãy nhập văn bản"
    )
    page.set_viewport_size({"width": 360, "height": 900})
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.screenshot(
        path=str(root / "docs/evidence/ui/voice-mobile.png"), full_page=True
    )
    (root / "docs/evidence/ui/m5-results.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "actual_asr_hypothesis": hypothesis,
                "speech_source": "synthetic eSpeak NG, recognition inaccurate; explicitly edited by test",
                "flows": [
                    "real offline ASR upload",
                    "editable transcript routes to common voice search",
                    "winter preference/puffer first after correction",
                    "permission denial fallback",
                    "503 UI fallback (intercepted response simulation)",
                    "360px no overflow",
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf8",
    )
    browser.close()
