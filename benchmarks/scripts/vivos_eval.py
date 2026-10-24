"""Rights-reviewed VIVOS human speech; academic local evaluation, never publish audio."""

import argparse
import hashlib
import io
import json
import time
import wave
from pathlib import Path

import httpx

from voice_integration import distance, normalized

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data/private/vivos"
URL = "https://huggingface.co/datasets/AILAB-VNUHCM/vivos/resolve/refs%2Fconvert%2Fparquet/default/test/0000.parquet"
SHA256 = "c37e8fc3cf5c4e446960cfa032683d74f759b5146ac475a087e1e327b0cf5d89"


def prepare():
    import pyarrow.parquet as pq

    STORE.mkdir(parents=True, exist_ok=True)
    archive = STORE / "test.parquet"
    if not archive.exists():
        temporary = archive.with_suffix(".partial")
        with httpx.stream("GET", URL, follow_redirects=True, timeout=90) as response:
            response.raise_for_status()
            with temporary.open("wb") as output:
                for chunk in response.iter_bytes(1024 * 1024):
                    output.write(chunk)
        temporary.replace(archive)
    with archive.open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != SHA256:
            raise RuntimeError("VIVOS archive hash changed; review source before use")
    selected = []
    counts = {}
    for row in pq.read_table(archive).to_pylist():
        raw = row["audio"]["bytes"]
        with wave.open(io.BytesIO(raw)) as audio:
            duration = audio.getnframes() / audio.getframerate()
        speaker = row["speaker_id"]
        if not 1 <= duration <= 12 or counts.get(speaker, 0) >= 2:
            continue
        identifier = Path(row["path"]).stem
        (STORE / (identifier + ".wav")).write_bytes(raw)
        selected.append(
            {
                "id": identifier,
                "speaker_id": speaker,
                "reference": row["sentence"].lower(),
                "duration_seconds": duration,
                "file": identifier + ".wav",
            }
        )
        counts[speaker] = counts.get(speaker, 0) + 1
        if len(selected) == 20:
            break
    manifest = {
        "source": URL,
        "sha256": SHA256,
        "bytes": archive.stat().st_size,
        "release": "https://zenodo.org/records/7068130",
        "license": "CC-BY-NC-SA-4.0",
        "authors": ["Hieu-Thi Luong", "Hai-Quan Vu"],
        "use": "Local academic evaluation only; quarantined, not public gallery",
        "samples": selected,
    }
    (STORE / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8"
    )
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="vivos-base.json")
    args = parser.parse_args()
    manifest = prepare()
    results = []
    with httpx.Client(
        base_url="http://127.0.0.1:8000", timeout=65, trust_env=False
    ) as client:
        for sample in manifest["samples"]:
            start = time.perf_counter()
            response = client.post(
                "/api/v1/search/voice",
                files={
                    "audio": (
                        sample["file"],
                        (STORE / sample["file"]).read_bytes(),
                        "audio/wav",
                    )
                },
            )
            response.raise_for_status()
            data = response.json()
            ref, hyp = normalized(sample["reference"]), normalized(data["text"])
            result = {
                **sample,
                "hypothesis": data["text"],
                "word_errors": distance(ref.split(), hyp.split()),
                "words": len(ref.split()),
                "character_errors": distance(ref, hyp),
                "characters": len(ref),
                "http_ms": round((time.perf_counter() - start) * 1000, 3),
                "inference_ms": data["inference_ms"],
                "recognizer": data["recognizer"],
            }
            results.append(result)
            print(
                json.dumps(
                    {"id": sample["id"], "wer": result["word_errors"] / result["words"]}
                ),
                flush=True,
            )
    report = {
        "scope": "20 unmodified human test recordings, first 2 qualifying per speaker, 10 speakers; no synthetic samples or dialect labels",
        "source": manifest["release"],
        "authors": manifest["authors"],
        "license": manifest["license"],
        "archive_sha256": SHA256,
        "samples": results,
        "wer": sum(r["word_errors"] for r in results)
        / sum(r["words"] for r in results),
        "cer": sum(r["character_errors"] for r in results)
        / sum(r["characters"] for r in results),
        "http_p95_ms": sorted(r["http_ms"] for r in results)[18],
        "limitations": "Read speech, small sample; not shopping/TC2 exact utterance, dialect, mixed-English or noise population proof",
    }
    (ROOT / "docs/evidence" / args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )


if __name__ == "__main__":
    main()
