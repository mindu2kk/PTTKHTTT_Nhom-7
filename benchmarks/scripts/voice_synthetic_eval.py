"""Actual ASR on six explicitly synthetic voices; no human dialect claim."""

import json
import subprocess
from pathlib import Path

import httpx

from voice_integration import distance, normalized

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = "tôi muốn mua áo mùa đông"


def run():
    results = []
    for voice in ["vi", "vi-vn-x-central", "vi-vn-x-south"]:
        for speed in [135, 170]:
            name = f"synthetic-{voice}-{speed}.wav"
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "hoodoomart-inference-1",
                    "espeak-ng",
                    "-v",
                    voice,
                    "-s",
                    str(speed),
                    "-w",
                    "/tmp/" + name,
                    REFERENCE,
                ],
                check=True,
                capture_output=True,
            )
            path = ROOT / "benchmarks/audio" / name
            subprocess.run(
                ["docker", "cp", "hoodoomart-inference-1:/tmp/" + name, str(path)],
                check=True,
                capture_output=True,
            )
            with httpx.Client(base_url="http://127.0.0.1:8000", timeout=60) as client:
                r = client.post(
                    "/api/v1/search/voice",
                    files={"audio": (name, path.read_bytes(), "audio/wav")},
                )
                r.raise_for_status()
                data = r.json()
                search = client.post(
                    "/api/v1/search/text", json={"q": data["text"], "modality": "voice"}
                )
                search.raise_for_status()
                found = search.json()
            ref = normalized(REFERENCE)
            hyp = normalized(data["text"])
            hard = found["query"]["hard_filters"]
            soft = found["query"]["soft_preferences"]
            result = {
                "voice": voice,
                "speed": speed,
                "reference": REFERENCE,
                "hypothesis": data["text"],
                "wer": distance(ref.split(), hyp.split()) / len(ref.split()),
                "cer": distance(ref, hyp) / len(ref),
                "duration_seconds": data["duration_seconds"],
                "inference_ms": data["inference_ms"],
                "model_load_ms": data["model_load_ms"],
                "winter_intent_correct": any(c["key"] == "season" for c in soft)
                and any(c["key"] == "category" for c in hard),
                "top_product": found["items"][0]["product"]["id"]
                if found["items"]
                else None,
            }
            results.append(result)
            print(json.dumps(result, ensure_ascii=True), flush=True)
    report = {
        "source": "eSpeak NG generated Vietnamese voices; synthetic, NOT human North/Central/South speech",
        "reference": REFERENCE,
        "runs": results,
        "mean_wer": sum(r["wer"] for r in results) / len(results),
        "mean_cer": sum(r["cer"] for r in results) / len(results),
        "intent_accuracy": sum(r["winter_intent_correct"] for r in results)
        / len(results),
        "limitations": "Six synthetic renderings of one sentence; insufficient for general ASR quality, human dialects, noise or mixed-language accuracy.",
    }
    (ROOT / "docs/evidence/voice-synthetic.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )


if __name__ == "__main__":
    run()
