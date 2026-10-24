"""Instrumented ASR response tests opt-in suggestions; final text retrieval is real HTTP."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/search-quality"
ORIGINAL = "tôi muốn mua tài nghe dưới năm trăm nghìn"
SUGGESTION = "tôi muốn mua tai nghe dưới năm trăm nghìn"


def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--use-fake-device-for-media-stream",
                "--use-fake-ui-for-media-stream",
            ],
        )
        for width in [390, 1280]:
            context = browser.new_context(
                permissions=["microphone"], viewport={"width": width, "height": 950}
            )
            page = context.new_page()
            searches = []
            page.on(
                "request",
                lambda r: searches.append(r.post_data_json)
                if r.url.endswith("/search/text") and r.method == "POST"
                else None,
            )
            page.route(
                "**/api/v1/search/voice",
                lambda route: route.fulfill(
                    json={
                        "text": ORIGINAL,
                        "suggestions": [SUGGESTION],
                        "warnings": [
                            "Tên sản phẩm chưa chắc chắn. Kiểm tra câu đã nhận."
                        ],
                        "language": "vi",
                        "duration_seconds": 1,
                        "recognizer": "instrumented-test-only",
                        "model_revision": "test-only",
                        "inference_ms": 0,
                        "model_load_ms": 0,
                    }
                ),
            )
            page.goto("http://localhost:3000/", wait_until="networkidle")
            page.get_by_role("button", name="Tìm bằng giọng nói", exact=True).click()
            modal = page.get_by_role("dialog", name="Tìm sản phẩm", exact=True)
            stop = modal.get_by_role("button", name="Dừng và nhận câu nói", exact=True)
            expect(stop).to_be_visible()
            page.wait_for_timeout(
                500
            )  # Explicit short recording, not an arbitrary UI readiness wait.
            stop.click()
            field = modal.get_by_label("Câu tìm kiếm", exact=True)
            expect(field).to_have_value(ORIGINAL)
            expect(
                modal.get_by_text(
                    "Tên sản phẩm chưa chắc chắn. Kiểm tra câu đã nhận.", exact=True
                )
            ).to_be_visible()
            assert not searches, (
                "ASR/alternative must not auto-submit a possibly wrong query"
            )
            assert modal.evaluate("e=>e.scrollWidth<=e.clientWidth")
            page.screenshot(path=str(OUT / f"voice-suggestion-{width}.png"))
            modal.get_by_role("button", name=SUGGESTION, exact=True).click()
            expect(field).to_have_value(SUGGESTION)
            assert not searches
            with page.expect_response(
                lambda r: r.url.endswith("/search/text") and r.request.method == "POST"
            ) as event:
                modal.get_by_role("button", name="Tìm", exact=True).click()
            response = event.value
            assert response.status == 200 and searches[-1]["q"] == SUGGESTION
            data = response.json()
            assert data["query"]["modality"] == "voice"
            budget = next(
                c for c in data["query"]["hard_filters"] if c["key"] == "price_max"
            )
            assert (budget["value"], budget["operator"]) == (500000, "lt")
            assert all(r["product"]["price_vnd"] < 500000 for r in data["items"])
            assert page.url == "http://localhost:3000/"
            assert modal.evaluate("e=>e.scrollWidth<=e.clientWidth")
            page.screenshot(path=str(OUT / f"voice-alternative-{width}.png"))
            results.append(
                {
                    "width": width,
                    "original_preserved": True,
                    "warning_visible": True,
                    "confirmation_required": True,
                    "real_voice_text_retrieval": response.status,
                }
            )
            context.close()
        browser.close()
    (OUT / "suggestion-browser.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "scope": "Instrumented ASR response and fake Chrome microphone; real BFF/text retrieval; not acoustic accuracy proof",
                "cases": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        "utf8",
    )
    print(
        "Opt-in voice suggestions passed at 390/1280px; real text retrieval, unchanged URL."
    )


if __name__ == "__main__":
    main()
