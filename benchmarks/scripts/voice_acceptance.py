"""TC2 actual uploaded audio -> real ASR -> unedited shared search; never invent a pass."""

import argparse
import hashlib
import json
import mimetypes
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from voice_integration import distance, normalized

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = "tôi muốn mua áo mùa đông"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    args = parser.parse_args()
    audio = args.audio.resolve(strict=True)
    mime = {
        ".wav": "audio/wav",
        ".webm": "audio/webm",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
    }.get(audio.suffix.lower()) or mimetypes.guess_type(audio.name)[0]
    raw = audio.read_bytes()
    with httpx.Client(
        base_url="http://localhost:8000", timeout=65, trust_env=False
    ) as client:
        start = time.perf_counter()
        response = client.post(
            "/api/v1/search/voice",
            files={"audio": (audio.name, raw, mime or "application/octet-stream")},
        )
        response.raise_for_status()
        transcript = response.json()
        transcription_http_ms = round((time.perf_counter() - start) * 1000, 3)
        response = client.post(
            "/api/v1/search/text", json={"q": transcript["text"], "modality": "voice"}
        )
        response.raise_for_status()
        result = response.json()
    query = result["query"]
    passed = bool(
        query["modality"] == "voice"
        and any(c["key"] == "category" for c in query["hard_filters"])
        and any(
            c["key"] == "season" and c["value"] == "mùa đông"
            for c in query["soft_preferences"]
        )
        and result["items"]
        and "Áo phao" in result["items"][0]["product"]["name_vi"]
    )
    reference = normalized(REFERENCE)
    hypothesis = normalized(transcript["text"])
    report = {
        "measured_at": datetime.now(UTC).isoformat(),
        "source": "User-supplied actual audio; no synthetic voice or transcript correction",
        "audio_sha256": hashlib.sha256(raw).hexdigest(),
        "reference": REFERENCE,
        "transcript": transcript,
        "wer": distance(reference.split(), hypothesis.split()) / len(reference.split()),
        "cer": distance(reference, hypothesis) / len(reference),
        "transcription_http_ms": transcription_http_ms,
        "query": query,
        "top_products": [r["product"]["id"] for r in result["items"][:3]],
        "retrieval_stages_ms": result["stages_ms"],
        "result": "passed" if passed else "failed",
        "raw_audio_retained_by_app": False,
    }
    (ROOT / "docs/evidence/tc2-user-audio.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )
    print(
        json.dumps(
            {
                "result": report["result"],
                "wer": report["wer"],
                "cer": report["cer"],
                "transcript": transcript["text"],
            },
            ensure_ascii=True,
        )
    )
    if not passed:
        raise SystemExit("TC2 unedited ASR did not preserve winter clothing intent")


if __name__ == "__main__":
    main()
