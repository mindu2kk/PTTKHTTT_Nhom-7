"""Simulated Chrome microphone device; actual MediaRecorder/WebM/Whisper path."""

import json
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chrome",
        headless=True,
        args=[
            "--use-fake-device-for-media-stream",
            "--use-fake-ui-for-media-stream",
            "--use-file-for-fake-audio-capture="
            + str(ROOT / "benchmarks/audio/course-tts.wav"),
        ],
    )
    context = browser.new_context(permissions=["microphone"])
    page = context.new_page()
    page.add_init_script(
        "window.__tracks=[];const g=navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);navigator.mediaDevices.getUserMedia=async c=>{const s=await g(c);window.__tracks.push(...s.getTracks());return s;};"
    )
    page.goto("http://localhost:3000/search/voice", wait_until="networkidle")
    page.get_by_role("button", name="Bắt đầu ghi âm").click()
    expect(page.get_by_role("button", name="Hủy bản ghi", exact=True)).to_be_visible()
    page.get_by_role("button", name="Hủy bản ghi", exact=True).click()
    assert page.evaluate(
        "window.__tracks.length>0 && window.__tracks.every(t=>t.readyState==='ended')"
    )
    expect(page.locator("audio")).to_have_count(0)
    page.get_by_role("button", name="Bắt đầu ghi âm").click()
    expect(
        page.get_by_role("button", name=re.compile(r"Dừng ghi · [3-9]s"))
    ).to_be_visible(timeout=12000)
    page.get_by_role("button", name=re.compile("Dừng ghi")).click()
    expect(page.locator("audio")).to_be_visible()
    assert page.evaluate("window.__tracks.every(t=>t.readyState==='ended')")
    page.get_by_role("button", name="Chuyển thành chữ").click()
    expect(page.get_by_label("Kiểm tra và sửa câu tìm kiếm")).not_to_have_value(
        "", timeout=60000
    )
    text = page.get_by_label("Kiểm tra và sửa câu tìm kiếm").input_value()
    (ROOT / "docs/evidence/ui/recording-results.json").write_text(
        json.dumps(
            {
                "result": "passed",
                "capture": "Chrome fake audio device playing synthetic eSpeak WAV, not a physical microphone",
                "pipeline": "actual MediaRecorder WebM -> bounded upload -> real local Whisper",
                "cancel_releases_tracks": True,
                "stop_releases_tracks": True,
                "hypothesis": text,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf8",
    )
    browser.close()
