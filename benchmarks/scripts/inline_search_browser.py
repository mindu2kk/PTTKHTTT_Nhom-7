"""Actual inline text/image/recording journeys; instrumented guards are labelled separately."""

import base64
import hashlib
import json
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(
    os.environ.get("INLINE_SEARCH_EVIDENCE", str(ROOT / "docs/evidence/inline-search"))
)
BASE = "http://localhost:3000"
TRACKS = """window.__tracks=[];window.__micCalls=0;
const original=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
navigator.mediaDevices.getUserMedia=async c=>{window.__micCalls++;const s=await original(c);window.__tracks.push(...s.getTracks());return s;};
window.__revoked=[];const revoke=URL.revokeObjectURL.bind(URL);URL.revokeObjectURL=u=>{window.__revoked.push(u);revoke(u);};"""


def dialog(page):
    return page.get_by_role("dialog", name="Tìm sản phẩm", exact=True)


def submit(page, path="text"):
    with page.expect_response(
        lambda r: r.url.endswith(f"/search/{path}") and r.request.method == "POST",
        timeout=65000,
    ) as event:
        dialog(page).get_by_role("button", name="Tìm", exact=True).click()
    return event.value


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = {"result": "passed", "viewports": [], "journeys": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        for width in [360, 390, 768, 1280, 1440]:
            context = browser.new_context(viewport={"width": width, "height": 950})
            page = context.new_page()
            page.add_init_script(TRACKS)
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(BASE, wait_until="networkidle")
            assert page.evaluate("window.__micCalls") == 0
            field = page.get_by_label("Tìm nhanh sản phẩm", exact=True)
            field.fill("tai nghe")
            with page.expect_response(
                lambda r: r.url.endswith("/search/text") and r.request.method == "POST"
            ) as event:
                field.press("Enter")
            response = event.value.json()
            assert event.value.status == 200 and response["items"]
            expect(dialog(page).locator(".product-card").first).to_be_visible()
            assert page.url == BASE + "/"
            assert not page.evaluate("document.documentElement.scrollWidth>innerWidth")
            assert dialog(page).evaluate("e=>e.scrollWidth<=e.clientWidth")
            page.screenshot(path=str(OUT / f"text-{width}.png"))
            page.keyboard.press("Escape")
            expect(dialog(page)).not_to_be_visible()
            expect(field).to_be_focused()
            assert not errors
            result["viewports"].append(
                {
                    "width": width,
                    "same_page_text": "passed",
                    "overflow": False,
                    "microphone_on_load": 0,
                }
            )
            context.close()
        context = browser.new_context(viewport={"width": 1280, "height": 950})
        page = context.new_page()
        page.add_init_script(TRACKS)
        page.goto(BASE, wait_until="networkidle")
        field = page.get_by_label("Tìm nhanh sản phẩm", exact=True)
        field.fill("giày")
        field.press("Enter")
        expect(dialog(page).locator(".product-card")).to_have_count(12, timeout=15000)
        with page.expect_response(
            lambda r: r.url.endswith("/search/text") and r.request.method == "POST"
        ) as event:
            dialog(page).get_by_role("button", name="Trang sau", exact=True).click()
        assert event.value.json()["page"] == 2 and page.url == BASE + "/"
        dialog(page).get_by_label("Câu tìm kiếm", exact=True).fill(
            "zzqqy không có sản phẩm"
        )
        assert submit(page).json()["total"] == 0
        expect(
            dialog(page).get_by_text("Chưa có sản phẩm khớp.", exact=False)
        ).to_be_visible()
        dialog(page).get_by_label("Câu tìm kiếm", exact=True).fill(
            "tra cứu đơn hàng 123456"
        )
        assert submit(page).status == 401
        expect(
            dialog(page).get_by_role("link", name="Đăng nhập", exact=True)
        ).to_be_visible()
        page.keyboard.press("Escape")
        result["journeys"].append({"pagination_empty_order_auth_same_url": "passed"})
        field.fill("")
        page.get_by_role("button", name="Tìm bằng hình ảnh", exact=True).click()
        selection = json.loads(
            (ROOT / "data/private/m8/heldout-selection.json").read_text(encoding="utf8")
        )
        photo = ROOT / "data/private/m8" / selection[0]["path"]
        dialog(page).get_by_label("Ảnh tìm kiếm tại chỗ", exact=True).set_input_files(
            str(photo)
        )
        image_response = submit(page, "image")
        assert image_response.status == 200 and image_response.json()["items"]
        assert image_response.json()["media"]["model_name"] == "OpenCLIP ViT-B/32"
        assert page.url == BASE + "/"
        expect(dialog(page).locator(".product-card").first).to_be_visible()
        page.wait_for_function(
            "() => [...document.querySelectorAll('.inline-search-results .product-card img')].slice(0,4).every(i=>i.complete&&i.naturalWidth>0)"
        )
        page.screenshot(path=str(OUT / "image-1280.png"))
        page.keyboard.press("Escape")
        assert page.evaluate("window.__revoked.length>0")
        # Synthetic clipboard event carries actual held-out image bytes to real CLIP API.
        field.evaluate(
            """(node,b64)=>{const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));const data=new DataTransfer();data.items.add(new File([bytes],'anh-da-dan.jpg',{type:'image/jpeg'}));node.dispatchEvent(new ClipboardEvent('paste',{clipboardData:data,bubbles:true,cancelable:true}));}""",
            base64.b64encode(photo.read_bytes()).decode(),
        )
        expect(dialog(page).get_by_alt_text("Ảnh bạn chọn để tìm kiếm")).to_be_visible()
        pasted = submit(page, "image")
        assert pasted.status == 200 and pasted.json()["items"]
        assert page.url == BASE + "/"
        dialog(page).get_by_role("button", name="Xóa ảnh đã chọn", exact=True).click()
        expect(dialog(page).get_by_alt_text("Ảnh bạn chọn để tìm kiếm")).to_have_count(
            0
        )
        dialog(page).get_by_label("Ảnh tìm kiếm tại chỗ", exact=True).set_input_files(
            {"name": "bad.jpg", "mimeType": "image/jpeg", "buffer": b"invalid image"}
        )
        assert submit(page, "image").status == 422
        expect(dialog(page).get_by_role("alert")).to_be_visible()
        dialog(page).get_by_label("Ảnh tìm kiếm tại chỗ", exact=True).set_input_files(
            {
                "name": "large.png",
                "mimeType": "image/png",
                "buffer": b"x" * (5 * 1024 * 1024 + 1),
            }
        )
        expect(dialog(page).get_by_role("alert")).to_contain_text("5 MB")
        page.keyboard.press("Escape")
        result["journeys"].append(
            {
                "upload_actual_clip_paste_event_delete_blob_cleanup_invalid_files": "passed",
                "paste_scope": "Browser ClipboardEvent injected by harness with real bytes; not OS clipboard automation",
                "image_vector_cached": image_response.json()["media"]["cached"],
            }
        )
        context.close()
        # Permission denied and delayed permission are lifecycle instrumentation, not inference proof.
        for late in [False, True]:
            context = browser.new_context()
            page = context.new_page()
            page.add_init_script(
                "window.__lateStops=0;navigator.mediaDevices.getUserMedia=()=>new Promise(resolve=>window.__grant=()=>resolve({getTracks:()=>[{stop:()=>window.__lateStops++}]}));"
                if late
                else "navigator.mediaDevices.getUserMedia=async()=>{throw new DOMException('denied','NotAllowedError')};"
            )
            page.goto(BASE, wait_until="networkidle")
            page.get_by_role("button", name="Tìm bằng giọng nói", exact=True).click()
            if late:
                expect(
                    dialog(page).get_by_text("Đang chờ quyền micro…", exact=True)
                ).to_be_visible()
                page.keyboard.press("Escape")
                page.evaluate("window.__grant()")
                page.wait_for_function("() => window.__lateStops===1")
                expect(dialog(page)).not_to_be_visible()
            else:
                expect(dialog(page).get_by_role("alert")).to_contain_text("quyền micro")
                dialog(page).get_by_label("Câu tìm kiếm", exact=True).fill("giày")
                assert submit(page).status == 200
            assert page.url == BASE + "/"
            context.close()
        result["journeys"].append(
            {"instrumented_denied_and_late_grant_ignored_tracks_stopped": "passed"}
        )
        browser.close()
        # Actual MediaRecorder/WebM/Whisper; fake microphone device plays a private human VIVOS clip.
        sample = json.loads(
            (ROOT / "data/private/vivos/samples.json").read_text(encoding="utf8")
        )[0]
        wav = ROOT / "data/private/vivos" / sample["file"]
        browser = p.chromium.launch(
            channel="chrome",
            headless=True,
            args=[
                "--use-fake-device-for-media-stream",
                "--use-fake-ui-for-media-stream",
                "--use-file-for-fake-audio-capture=" + str(wav),
            ],
        )
        context = browser.new_context(
            permissions=["microphone"], viewport={"width": 390, "height": 950}
        )
        page = context.new_page()
        page.add_init_script(TRACKS)
        target = BASE + "/products?category=gia-dung&price_max=1000000"
        page.goto(target, wait_until="networkidle")
        assert page.evaluate("window.__micCalls") == 0
        page.get_by_role("button", name="Tìm bằng giọng nói", exact=True).click()
        expect(
            dialog(page).get_by_role("button", name="Dừng và nhận câu nói", exact=True)
        ).to_be_visible()
        page.keyboard.press("Escape")
        assert page.evaluate(
            "window.__tracks.length>0&&window.__tracks.every(t=>t.readyState==='ended')"
        )
        page.get_by_role("button", name="Tìm bằng giọng nói", exact=True).click()
        expect(dialog(page).locator(".inline-search-status")).to_contain_text(
            re.compile(r"[3-9]s / 12s"), timeout=15000
        )
        page.screenshot(path=str(OUT / "voice-recording-390.png"))
        with page.expect_response(
            lambda r: r.url.endswith("/search/voice") and r.request.method == "POST",
            timeout=65000,
        ) as event:
            dialog(page).get_by_role(
                "button", name="Dừng và nhận câu nói", exact=True
            ).click()
        assert event.value.status == 200, event.value.text()
        transcript = event.value.json()["text"]
        assert transcript and len(transcript) <= 300
        expect(dialog(page).get_by_label("Câu tìm kiếm", exact=True)).to_have_value(
            transcript
        )
        assert page.evaluate("window.__tracks.every(t=>t.readyState==='ended')")
        assert page.url == target
        page.screenshot(path=str(OUT / "voice-review-390.png"))
        dialog(page).get_by_label("Câu tìm kiếm", exact=True).fill("ghế")
        voice_search = submit(page)
        data = voice_search.json()
        assert (
            voice_search.status == 200
            and data["query"]["modality"] == "voice"
            and data["items"]
        )
        assert all(row["product"]["price_vnd"] <= 1000000 for row in data["items"])
        assert page.url == target
        page.keyboard.press("Escape")
        page.get_by_role("button", name="Tìm bằng giọng nói", exact=True).click()
        expect(
            dialog(page).get_by_role("button", name="Dừng và nhận câu nói", exact=True)
        ).to_be_visible()
        page.evaluate(
            "Object.defineProperty(document,'hidden',{configurable:true,get:()=>true});document.dispatchEvent(new Event('visibilitychange'))"
        )
        expect(
            dialog(page).get_by_text("Đã dừng ghi âm khi bạn rời trang.", exact=True)
        ).to_be_visible()
        assert page.evaluate("window.__tracks.every(t=>t.readyState==='ended')")
        page.evaluate("delete document.hidden")
        page.keyboard.press("Escape")
        # SPA query navigation must unmount the controller and release an active recorder.
        page.get_by_role("button", name="Tìm bằng giọng nói", exact=True).click()
        expect(
            dialog(page).get_by_role("button", name="Dừng và nhận câu nói", exact=True)
        ).to_be_visible()
        page.evaluate("history.pushState(null,'','/products?category=gia-dung')")
        page.wait_for_function("() => window.__tracks.every(t=>t.readyState==='ended')")
        expect(dialog(page)).not_to_be_visible()
        result["journeys"].append(
            {
                "actual_record_stop_whisper_correct_voice_search_scope_cleanup_spa_navigation": "passed",
                "capture": "Chrome fake microphone playing VIVOS human WAV; not a physical microphone or TC2",
                "sample_id": sample["id"],
                "asr_recognizer": event.value.json()["recognizer"],
                "transcript_length": len(transcript),
                "transcript_sha256": hashlib.sha256(transcript.encode()).hexdigest(),
                "source_audio_not_redistributed": True,
            }
        )
        browser.close()
    (OUT / "browser.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(
        "Inline search passed: five viewport text flows, actual image/paste retrieval, permissions, actual recording/ASR, voice search and cleanup."
    )


if __name__ == "__main__":
    main()
