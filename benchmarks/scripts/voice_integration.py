"""Actual local ASR on labelled synthetic speech; not a human accent benchmark."""

import io
import json
import statistics
import time
import unicodedata
import wave
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]


def distance(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        new = [i]
        for j, y in enumerate(b, 1):
            new.append(min(new[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = new
    return row[-1]


def normalized(s):
    return "".join(
        c for c in unicodedata.normalize("NFC", s.lower()) if c.isalnum() or c.isspace()
    ).strip()


def run():
    reference = "tôi muốn mua áo mùa đông"
    raw = (ROOT / "benchmarks/audio/course-tts.wav").read_bytes()
    results = []
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=60) as client:
        for _ in range(5):
            started = time.perf_counter()
            response = client.post(
                "/api/v1/search/voice",
                files={"audio": ("course.wav", raw, "audio/wav")},
            )
            response.raise_for_status()
            results.append(
                {"http_ms": (time.perf_counter() - started) * 1000, **response.json()}
            )
        negatives = {}
        for name, seconds, amplitude in [("silence", 1, 0), ("too_long", 16, 5000)]:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
                output.writeframes(
                    int(amplitude).to_bytes(2, "little", signed=True) * 16000 * seconds
                )
            r = client.post(
                "/api/v1/search/voice",
                files={"audio": ("clip.wav", buf.getvalue(), "audio/wav")},
            )
            assert r.status_code == 422, r.text
            negatives[name] = r.status_code
        for name, raw_bad, mime in [
            ("corrupt", b"RIFF0000WAVEbad", "audio/wav"),
            ("unsupported", b"text", "text/plain"),
        ]:
            r = client.post(
                "/api/v1/search/voice", files={"audio": ("clip.wav", raw_bad, mime)}
            )
            assert r.status_code == 422
            negatives[name] = r.status_code
        correction = client.get(
            "/api/v1/search/text", params={"q": reference, "modality": "voice"}
        ).json()
        assert correction["query"]["modality"] == "voice"
        assert any(
            f["key"] == "season" for f in correction["query"]["soft_preferences"]
        )
        hypothesis = normalized(results[0]["text"])
        ref = normalized(reference)
        report = {
            "speech_source": "eSpeak NG vi synthetic, no human or regional claim",
            "reference": reference,
            "hypothesis": hypothesis,
            "wer": distance(ref.split(), hypothesis.split()) / len(ref.split()),
            "cer": distance(ref, hypothesis) / len(ref),
            "runs": results,
            "negative_statuses": negatives,
            "warm_http_median_ms": statistics.median(r["http_ms"] for r in results[1:]),
            "edited_query_top": correction["items"][0]["product"]["id"],
            "limitation": "TC2 transcript is inaccurate on this synthetic sample. User correction works; human accent acceptance remains unproven.",
        }
        (ROOT / "docs/evidence/voice-integration.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
        )
        print(
            json.dumps(
                {k: v for k, v in report.items() if k != "runs"}, ensure_ascii=True
            )
        )


if __name__ == "__main__":
    run()
