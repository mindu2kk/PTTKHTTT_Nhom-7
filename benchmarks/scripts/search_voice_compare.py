"""Paired local ASR evaluation; never downloads data or confuses TTS with human speech."""

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from voice_integration import distance, normalized

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/evidence/search-quality"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["before", "after"])
    args = parser.parse_args()
    samples = [
        {**s, "path": ROOT / "data/private/vivos" / s["file"], "group": "human_read"}
        for s in json.loads(
            (ROOT / "data/private/vivos/samples.json").read_text("utf8")
        )
    ]
    samples += [
        {
            "id": p.stem,
            "path": p,
            "reference": "tôi muốn mua áo mùa đông",
            "group": "synthetic_shopping",
        }
        for p in sorted((ROOT / "benchmarks/audio").glob("*.wav"))
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    results = []
    with httpx.Client(
        base_url="http://127.0.0.1:8000", timeout=65, trust_env=False
    ) as client:
        for sample in samples:
            raw = sample["path"].read_bytes()
            started = time.perf_counter()
            response = client.post(
                "/api/v1/search/voice",
                files={"audio": ("sample.wav", raw, "audio/wav")},
            )
            data = response.json()
            ref, hyp = normalized(sample["reference"]), normalized(data.get("text", ""))
            results.append(
                {
                    "id": sample["id"],
                    "group": sample["group"],
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "reference": sample["reference"],
                    "status": response.status_code,
                    "hypothesis": data.get("text", ""),
                    "word_errors": distance(ref.split(), hyp.split()),
                    "words": len(ref.split()),
                    "character_errors": distance(ref, hyp),
                    "characters": len(ref),
                    "http_ms": round((time.perf_counter() - started) * 1000, 3),
                    "warnings": data.get("warnings", []),
                }
            )
            print(
                f"{args.stage}: {sample['id']} HTTP{response.status_code}", flush=True
            )
    groups = {}
    for group in {s["group"] for s in results}:
        rows = [s for s in results if s["group"] == group]
        groups[group] = {
            "samples": len(rows),
            "http_errors": sum(s["status"] != 200 for s in rows),
            "wer": sum(s["word_errors"] for s in rows) / sum(s["words"] for s in rows),
            "cer": sum(s["character_errors"] for s in rows)
            / sum(s["characters"] for s in rows),
            "mean_http_ms": sum(s["http_ms"] for s in rows) / len(rows),
        }
    report = {
        "measured_at": datetime.now(UTC).isoformat(),
        "stage": args.stage,
        "groups": groups,
        "samples": results,
        "limitations": "VIVOS read speech CC-BY-NC-SA4.0 (Luong & Vu), not shopping; eSpeak shopping is synthetic, not TC2 or human shopping accuracy. No audio redistributed.",
    }
    if args.stage == "after":
        before = json.loads((OUT / "asr-before.json").read_text("utf8"))
        assert [(s["id"], s["sha256"]) for s in before["samples"]] == [
            (s["id"], s["sha256"]) for s in results
        ], "Comparison must use exactly the same audio"
        report["paired_delta_wer"] = {
            g: groups[g]["wer"] - before["groups"][g]["wer"] for g in groups
        }
    (OUT / f"asr-{args.stage}.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), "utf8"
    )
    print(json.dumps(groups), flush=True)


if __name__ == "__main__":
    main()
