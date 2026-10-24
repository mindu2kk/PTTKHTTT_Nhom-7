"""Loopback-only, opt-in recording collection for the frozen shopping voice oracle.

No inference or downloads. Audio stays in the ignored data/private tree. This is
evaluation tooling, not an application endpoint or evidence of voice quality.
"""

import argparse
import hashlib
import json
import secrets
import threading
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORACLE = ROOT / "benchmarks/fixtures/shopping_intent_cases.json"
PRIVATE = ROOT / "data/private/shopping-voice"
MAX_AUDIO = 2 * 1024 * 1024
TYPES = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/wav": ".wav", "audio/mp4": ".m4a"}


def valid_audio(raw: bytes, mime: str) -> bool:
    return {
        "audio/webm": raw.startswith(b"\x1a\x45\xdf\xa3"),
        "audio/ogg": raw.startswith(b"OggS"),
        "audio/wav": raw.startswith(b"RIFF") and raw[8:12] == b"WAVE",
        "audio/mp4": raw[4:8] == b"ftyp",
    }.get(mime, False)


class CaptureServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, port: int):
        raw = ORACLE.read_bytes()
        self.oracle = json.loads(raw)
        self.oracle_hash = hashlib.sha256(raw).hexdigest()
        self.token = secrets.token_urlsafe(32)
        self.write_lock = threading.Lock()
        self.session = secrets.token_hex(12)
        self.manifest = {
            "version": 1,
            "oracle_path": ORACLE.relative_to(ROOT).as_posix(),
            "oracle_sha256": self.oracle_hash,
            "records": [],
        }
        super().__init__(("127.0.0.1", port), Handler)


class Handler(BaseHTTPRequestHandler):
    server: CaptureServer

    def log_message(self, *_args):
        pass  # Do not put recording identifiers or request bodies in access logs.

    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def reply(self, status: int, data, mime: str = "application/json"):
        raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; media-src blob:; connect-src 'self'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(raw)

    def local_host(self) -> bool:
        return self.headers.get("Host") in {
            f"localhost:{self.server.server_port}", f"127.0.0.1:{self.server.server_port}"
        }

    def do_GET(self):
        if not self.local_host():
            return self.reply(403, {"detail": "Chỉ truy cập từ máy này."})
        if self.path == "/":
            return self.reply(200, (ROOT / "benchmarks/capture/index.html").read_bytes(), "text/html")
        if self.path in {"/capture.js", "/capture.css"}:
            mime = "text/javascript" if self.path.endswith(".js") else "text/css"
            return self.reply(200, (ROOT / "benchmarks/capture" / self.path[1:]).read_bytes(), mime)
        if self.path == "/cases":
            return self.reply(200, {"token": self.server.token, "oracle": self.server.oracle, "session": self.server.session})
        self.reply(404, {"detail": "Không có trang này."})

    def do_POST(self):
        if not self.local_host() or self.path != "/record":
            return self.reply(403, {"detail": "Yêu cầu không hợp lệ."})
        if self.headers.get("Origin") != f"http://{self.headers.get('Host')}":
            return self.reply(403, {"detail": "Nguồn gửi không hợp lệ."})
        if not secrets.compare_digest(self.headers.get("X-Capture-Token", ""), self.server.token):
            return self.reply(403, {"detail": "Phiên ghi âm không hợp lệ."})
        if self.headers.get("Transfer-Encoding"):
            return self.reply(413, {"detail": "Bản ghi phải có dung lượng xác định."})
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            return self.reply(400, {"detail": "Dung lượng không hợp lệ."})
        if not 0 < size <= MAX_AUDIO:
            return self.reply(413, {"detail": "Bản ghi tối đa 2 MB."})
        cases = self.server.oracle.get("cases", [])
        case_id = self.headers.get("X-Case-Id", "")
        if case_id not in {row.get("id", row.get("case_id")) for row in cases}:
            return self.reply(422, {"detail": "Câu chưa có trong bộ đáp án đã khóa."})
        if self.headers.get("X-Recording-Consent") != "yes":
            return self.reply(422, {"detail": "Cần đồng ý lưu bản ghi để đánh giá."})
        mime = self.headers.get("Content-Type", "").split(";")[0]
        if mime not in TYPES:
            return self.reply(415, {"detail": "Định dạng âm thanh chưa hỗ trợ."})
        try:
            raw = self.rfile.read(size)
        except (TimeoutError, OSError):
            return self.reply(408, {"detail": "Hết thời gian nhận bản ghi."})
        if len(raw) != size or not valid_audio(raw, mime):
            return self.reply(422, {"detail": "Tệp không đúng định dạng âm thanh."})
        # Recheck the oracle has not changed since opening the page.
        if hashlib.sha256(ORACLE.read_bytes()).hexdigest() != self.server.oracle_hash:
            return self.reply(409, {"detail": "Bộ đáp án đã đổi; hãy mở lại công cụ."})
        with self.server.write_lock:
            folder = PRIVATE / self.server.session
            folder.mkdir(parents=True, exist_ok=True)
            record_id = secrets.token_hex(12)
            audio_path = folder / (record_id + TYPES[mime])
            with audio_path.open("xb") as output:
                output.write(raw)
            record = {
                "id": record_id, "case_id": case_id,
                "path": audio_path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(), "mime": mime,
                "audio_kind": "human", "speaker_id": "anon-" + self.server.session,
                "capture_mode": "live_microphone", "consent": True,
                "rights_status": "user_consent", "split": "heldout",
                "recorded_at": datetime.now(UTC).isoformat(),
            }
            self.server.manifest["records"].append(record)
            temporary = folder / "manifest.tmp"
            temporary.write_text(json.dumps(self.server.manifest, ensure_ascii=False, indent=2), encoding="utf8")
            temporary.replace(folder / "manifest.json")
        self.reply(201, {"saved": True, "case_id": case_id, "recordings": len(self.server.manifest["records"])})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8877)
    args = parser.parse_args()
    with CaptureServer(args.port) as server:
        print(f"Thu âm tự nguyện tại http://localhost:{server.server_port}; Ctrl+C để dừng.", flush=True)
        print("Chỉ lưu khi bấm Lưu bản ghi; không gửi audio ra ngoài máy.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
