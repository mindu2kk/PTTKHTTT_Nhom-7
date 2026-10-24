"""Real HTTP negative checks for the opt-in, private recording collector."""

import hashlib
import json
import socket
import threading

import httpx
import pytest

import shopping_capture as capture


@pytest.fixture
def collector(tmp_path, monkeypatch):
    oracle = tmp_path / "oracle.json"
    oracle.write_text(json.dumps({"cases": [{"id": "SV001", "query": "Tìm giày"}]}))
    monkeypatch.setattr(capture, "ROOT", tmp_path)
    monkeypatch.setattr(capture, "ORACLE", oracle)
    monkeypatch.setattr(capture, "PRIVATE", tmp_path / "data/private/shopping-voice")
    server = capture.CaptureServer(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    with httpx.Client(base_url=f"http://127.0.0.1:{server.server_port}", trust_env=False) as client:
        yield server, client
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)


def headers(server):
    return {
        "Origin": f"http://127.0.0.1:{server.server_port}",
        "X-Capture-Token": server.token,
        "X-Recording-Consent": "yes",
        "X-Case-Id": "SV001",
        "Content-Type": "audio/webm",
    }


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"Host": "attacker.example"}, 403),
        ({"Origin": "https://attacker.example"}, 403),
        ({"X-Capture-Token": "wrong"}, 403),
        ({"X-Recording-Consent": "no"}, 422),
        ({"X-Case-Id": "../../outside"}, 422),
        ({"Content-Type": "text/plain"}, 415),
    ],
)
def test_invalid_request_cannot_write_audio(collector, changes, expected):
    server, client = collector
    response = client.post("/record", headers={**headers(server), **changes}, content=b"\x1aE\xdf\xa3demo")
    assert response.status_code == expected
    assert not capture.PRIVATE.exists()


def test_fake_audio_and_oversize_cannot_be_saved(collector):
    server, client = collector
    assert client.post("/record", headers=headers(server), content=b"not audio").status_code == 422
    # Reject from headers without reading a giant body. Sending the full body
    # concurrently with a closed HTTP/1.0 socket can cause a Windows TCP reset.
    lines = {**headers(server), "Host": f"127.0.0.1:{server.server_port}", "Content-Length": str(capture.MAX_AUDIO + 1)}
    request = "POST /record HTTP/1.0\r\n" + "".join(f"{k}: {v}\r\n" for k, v in lines.items()) + "\r\n"
    with socket.create_connection(("127.0.0.1", server.server_port), timeout=3) as connection:
        connection.sendall(request.encode())
        assert connection.recv(1024).startswith(b"HTTP/1.0 413")
    assert not capture.PRIVATE.exists()


def test_oracle_change_requires_new_capture_session(collector):
    server, client = collector
    capture.ORACLE.write_text("{}")
    assert client.post("/record", headers=headers(server), content=b"\x1aE\xdf\xa3demo").status_code == 409
    assert not capture.PRIVATE.exists()


def test_explicit_save_writes_private_original_hash_and_frozen_oracle(collector):
    server, client = collector
    raw = b"\x1aE\xdf\xa3demo"  # Signature fixture only; not an ASR or human quality test.
    response = client.post("/record", headers=headers(server), content=raw)
    assert response.status_code == 201
    manifest = json.loads((capture.PRIVATE / server.session / "manifest.json").read_text())
    record = manifest["records"][0]
    assert manifest["oracle_sha256"] == hashlib.sha256(capture.ORACLE.read_bytes()).hexdigest()
    assert (capture.ROOT / record["path"]).read_bytes() == raw
    assert record["sha256"] == hashlib.sha256(raw).hexdigest()
    assert record["consent"] is True and record["capture_mode"] == "live_microphone"
    assert record["split"] == "heldout"
