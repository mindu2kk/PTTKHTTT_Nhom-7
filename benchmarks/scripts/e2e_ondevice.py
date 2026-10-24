"""Browser-provider UI contracts simulated explicitly; not speech accuracy evidence."""

import json
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
MOCK = """
window.__localSpeech={installs:0, starts:[], aborts:0};
class Speech {
 static status='downloadable';
 static async available(){return this.status}
 static async install(){window.__localSpeech.installs++;this.status='available';return true}
 start(){
  window.__localSpeech.starts.push({local:this.processLocally,lang:this.lang});
  window.__activeRecognition=this;
  if(window.__speechScenario==='success')setTimeout(()=>{this.onresult?.({results:[[{transcript:'tôi muốn mua áo mùa đông'}]]});this.onend?.()},30);
  if(window.__speechScenario==='denied')setTimeout(()=>{this.onerror?.({error:'not-allowed'});this.onend?.()},30);
 }
 stop(){}
 abort(){window.__localSpeech.aborts++;this.onend?.()}
}
Speech.prototype.processLocally=false;
window.SpeechRecognition=Speech;window.webkitSpeechRecognition=Speech;
"""


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 360, "height": 900})
        page.add_init_script(MOCK)
        requests = []
        page.on(
            "request",
            lambda r: requests.append(r.url)
            if "/search/voice" in r.url and r.method == "POST"
            else None,
        )
        page.goto("http://localhost:3000/search/voice", wait_until="networkidle")
        install = page.get_by_role(
            "button", name="Tải gói tiếng Việt (một lần)", exact=True
        )
        expect(install).to_be_visible()
        assert page.evaluate("window.__localSpeech.installs") == 0
        install.click()
        start = page.get_by_role(
            "button", name="Bắt đầu nhận giọng trên thiết bị", exact=True
        )
        expect(start).to_be_visible()
        page.evaluate("window.__speechScenario='denied'")
        start.click()
        expect(
            page.get_by_role("region", name="Nhận giọng trên thiết bị")
        ).to_contain_text("Chưa được cấp quyền micro")
        page.evaluate("window.__speechScenario='hang'")
        start.click()
        page.get_by_role("button", name="Hủy nhận giọng", exact=True).click()
        expect(start).to_be_visible()
        expect(
            page.get_by_role("button", name="Bắt đầu ghi âm", exact=True)
        ).to_be_enabled()
        # Late callbacks after cancellation cannot fill a transcript.
        page.evaluate(
            "window.__activeRecognition.onresult?.({results:[[{transcript:'late private speech'}]]})"
        )
        expect(page.get_by_label("Kiểm tra và sửa câu tìm kiếm")).to_have_value("")
        page.clock.install()
        start.click()
        page.clock.fast_forward(12000)
        page.clock.fast_forward(4000)
        expect(start).to_be_visible()
        expect(
            page.get_by_role("region", name="Nhận giọng trên thiết bị")
        ).to_contain_text("thời gian cho phép")
        page.evaluate("window.__speechScenario='success'")
        start.click()
        page.clock.fast_forward(100)
        expect(page.get_by_label("Kiểm tra và sửa câu tìm kiếm")).to_have_value(
            "tôi muốn mua áo mùa đông"
        )
        local = page.evaluate("window.__localSpeech")
        assert local["installs"] == 1
        assert all(s == {"local": True, "lang": "vi-VN"} for s in local["starts"])
        assert not requests, "On-device mode must not upload to Whisper"
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        page.screenshot(
            path=str(ROOT / "docs/evidence/ui/voice-ondevice-mobile.png"),
            full_page=True,
        )
        page.get_by_role("button", name="Tìm bằng câu đã sửa", exact=True).click()
        expect(page.locator(".product-card").first).to_contain_text("Áo phao")
        assert "modality=voice" in page.url
        unsupported = browser.new_page()
        unsupported.add_init_script(
            "window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined"
        )
        unsupported.goto("http://localhost:3000/search/voice", wait_until="networkidle")
        expect(
            unsupported.get_by_role("region", name="Nhận giọng trên thiết bị")
        ).to_contain_text("chưa hỗ trợ")
        expect(
            unsupported.get_by_label("Kiểm tra và sửa câu tìm kiếm")
        ).to_be_editable()
        report = {
            "result": "passed",
            "scope": "Explicitly simulated browser SpeechRecognition API callbacks, not real recognition or model quality",
            "flows": [
                "no automatic pack download",
                "explicit install",
                "processLocally always true",
                "no server ASR upload",
                "permission error",
                "cancel and ignore late result",
                "15s watchdog if engine hangs",
                "common voice pipeline after callback",
                "unsupported fallback",
                "360px no overflow",
            ],
            "provider_calls": local,
        }
        (ROOT / "docs/evidence/ui/ondevice-results.json").write_text(
            json.dumps(report, indent=2), encoding="utf8"
        )
        browser.close()


if __name__ == "__main__":
    main()
