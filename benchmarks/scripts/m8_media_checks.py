"""Actual M8 ASR/media/BFF smoke checks; not canonical TC2 acceptance."""

import hashlib
import json
import time
from pathlib import Path

import httpx

from voice_integration import distance, normalized

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/m8"


def main():
    sample = json.loads(
        (ROOT / "data/private/vivos/samples.json").read_text(encoding="utf8")
    )[0]
    audio = (ROOT / "data/private/vivos" / sample["file"]).read_bytes()
    with httpx.Client(
        base_url="http://localhost:3000",
        timeout=65,
        follow_redirects=False,
        headers={"Origin": "http://localhost:3000"},
    ) as client:
        started = time.perf_counter()
        response = client.post(
            "/api/v1/search/voice", files={"audio": ("human.wav", audio, "audio/wav")}
        )
        response.raise_for_status()
        result = response.json()
        reference = normalized(sample["reference"])
        transcript = normalized(result["text"])
        report = {
            "sample_id": sample["id"],
            "source": "VIVOS, Luong & Vu, CC-BY-NC-SA-4.0, private academic test only",
            "duration_seconds": sample["duration_seconds"],
            "sha256": hashlib.sha256(audio).hexdigest(),
            "asr_http_ms": round((time.perf_counter() - started) * 1000, 3),
            "recognizer": result["recognizer"],
            "inference_ms": result["inference_ms"],
            "model_load_ms": result["model_load_ms"],
            "wer": distance(reference.split(), transcript.split())
            / max(1, len(reference.split())),
            "scope": "One real human nonshopping clip; confirms actual local ASR adapter. Not TC2 or a quality benchmark; no transcript/audio redistributed",
        }
        voice = client.post(
            "/api/v1/search/text", json={"q": result["text"], "modality": "voice"}
        )
        assert voice.status_code == 200 and voice.json()["query"]["modality"] == "voice"
        bad_image = client.post(
            "/api/v1/search/image",
            files={"image": ("bad.jpg", b"not image", "image/jpeg")},
        )
        assert bad_image.status_code == 422
        bad_audio = client.post(
            "/api/v1/search/voice",
            files={"audio": ("bad.wav", b"not audio", "audio/wav")},
        )
        assert bad_audio.status_code == 422
        product = client.get("/api/v1/products").json()["items"][0]
        invalid = client.post(
            "/cart/add",
            data={"id": product["id"], "quantity": "1"},
            headers={
                "Origin": "http://localhost:3000",
                "Cookie": 'hm_cart={"id":"bad"}',
            },
        )
        assert invalid.status_code == 422
        valid = client.post(
            "/cart/add",
            data={"id": product["id"], "quantity": "1"},
            headers={"Origin": "http://localhost:3000"},
        )
        assert (
            valid.status_code == 303
            and valid.headers["location"] == "http://localhost:3000/cart"
        )
        report["guards"] = {
            "corrupt_image": bad_image.status_code,
            "corrupt_audio": bad_audio.status_code,
            "invalid_cart_cookie": invalid.status_code,
            "valid_nojs_cart": valid.status_code,
            "actual_transcript_shared_voice_pipeline": voice.status_code,
        }
        (OUT / "media-checks.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
