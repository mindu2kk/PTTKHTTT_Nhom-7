"""ViMD regional smoke evaluation; original supplied WAVs stay quarantined/unmodified."""

import hashlib
import io
import json
import time
import wave
from pathlib import Path

import httpx

from voice_integration import distance, normalized

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data/private/vimd"
SHARD_URL = "https://huggingface.co/datasets/nguyendv02/ViMD_Dataset/resolve/main/data/test-00008-of-00014.parquet"
SHARD_SHA256 = "d617472eb2880ed1c74352381f3158cf77891694e6647f4c01dd547ce18107eb"


def save_sample(row, raw, samples):
    region = row["region"]
    if sum(s["region"] == region for s in samples) >= 3 or len(raw) > 2 * 1024 * 1024:
        return
    try:
        with wave.open(io.BytesIO(raw)) as audio:
            duration = audio.getnframes() / audio.getframerate()
        if not 1 <= duration <= 15:
            return
    except (wave.Error, EOFError):
        return
    identifier = Path(row["filename"]).stem
    file = f"{region}-{identifier}.wav"
    (STORE / file).write_bytes(raw)
    samples.append(
        {
            "file": file,
            "id": identifier,
            "region": region,
            "speaker_id": row["speakerID"],
            "reference": row["text"],
            "duration_seconds": duration,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
    )


def prepare():
    import pyarrow.parquet as pq

    STORE.mkdir(parents=True, exist_ok=True)
    selection = STORE / "regional-selection.json"
    if selection.exists():
        cached = json.loads(selection.read_text(encoding="utf8"))
        if len(cached["samples"]) == 9:
            for sample in cached["samples"]:
                with (STORE / sample["file"]).open("rb") as source:
                    if (
                        hashlib.file_digest(source, "sha256").hexdigest()
                        != sample["sha256"]
                    ):
                        raise RuntimeError(
                            "Private audio changed; do not silently replace benchmark data"
                        )
            return cached
    samples = []
    # The public dataset filter index failed; readable row windows supply North/Central.
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        for offset in [0, 700]:
            metadata = client.get(
                "https://datasets-server.huggingface.co/rows",
                params={
                    "dataset": "nguyendv02/ViMD_Dataset",
                    "config": "default",
                    "split": "test",
                    "offset": offset,
                    "length": 100,
                },
            )
            if metadata.status_code != 200:
                raise RuntimeError(
                    f"Dataset metadata unavailable ({metadata.status_code}); no regional claim"
                )
            (STORE / f"rows-{offset}.json").write_text(metadata.text, encoding="utf8")
            rows = json.loads(
                (STORE / f"rows-{offset}.json").read_text(encoding="utf8")
            )["rows"]
            for item in rows:
                row = item["row"]
                if sum(s["region"] == row["region"] for s in samples) >= 3:
                    break
                if not 3 <= len(row["text"].split()) <= 35:
                    continue
                url = row["audio"][0]["src"]
                with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        raise RuntimeError(
                            f"Dataset audio unavailable ({response.status_code})"
                        )
                    if (
                        int(response.headers.get("content-length", "0"))
                        > 2 * 1024 * 1024
                    ):
                        continue
                    raw = bytearray()
                    for chunk in response.iter_bytes(65536):
                        raw.extend(chunk)
                        if len(raw) > 2 * 1024 * 1024:
                            break
                save_sample(row, bytes(raw), samples)
    shard = STORE / "test-00008.parquet"
    if not shard.exists():
        # Explicit benchmark command only, ~463MB source shard; never app/setup.
        with httpx.stream(
            "GET", SHARD_URL, follow_redirects=True, timeout=90
        ) as response:
            response.raise_for_status()
            with shard.with_suffix(".partial").open("wb") as output:
                for chunk in response.iter_bytes(1024 * 1024):
                    output.write(chunk)
        shard.with_suffix(".partial").replace(shard)
    with shard.open("rb") as source:
        if hashlib.file_digest(source, "sha256").hexdigest() != SHARD_SHA256:
            raise RuntimeError(
                "ViMD source hash changed; review rights/revision before use"
            )
    parquet = pq.ParquetFile(shard)
    for batch in parquet.iter_batches(batch_size=1):
        row = batch.to_pylist()[0]
        if row["region"] != "South" or not 3 <= len(row["text"].split()) <= 35:
            continue
        save_sample(row, row["audio"]["bytes"], samples)
        if sum(s["region"] == "South" for s in samples) == 3:
            break
    manifest = {
        "source": "https://huggingface.co/datasets/nguyendv02/ViMD_Dataset",
        "paper": "https://aclanthology.org/2024.emnlp-main.426/",
        "authors": ["Nguyen Dinh", "Thanh Dang", "Luan Thanh Nguyen", "Kiet Nguyen"],
        "license": "CC-BY-NC-ND-4.0",
        "scope": "Academic private evaluation; delivered WAV bytes retained unchanged, no cutting/reencoding/audio redistribution",
        "selection": "First 3 fitting 1..15s/2MB per source region, text3..35 words; API windows0/700, original test shard00008 for South",
        "samples": samples,
    }
    (STORE / "regional-selection.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf8"
    )
    assert len(samples) == 9 and {s["region"] for s in samples} == {
        "North",
        "Central",
        "South",
    }, "Not enough eligible original samples; do not invent regional coverage"
    return manifest


def main():
    manifest = prepare()
    results = []
    with httpx.Client(
        base_url="http://localhost:8000", timeout=65, trust_env=False
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
            data = response.json()
            hypothesis = data["text"] if response.status_code == 200 else ""
            ref, hyp = normalized(sample["reference"]), normalized(hypothesis)
            result = {k: v for k, v in sample.items() if k not in ["file", "reference"]}
            result.update(
                status=response.status_code,
                words=len(ref.split()),
                word_errors=distance(ref.split(), hyp.split()),
                characters=len(ref),
                character_errors=distance(ref, hyp),
                http_ms=round((time.perf_counter() - start) * 1000, 3),
                inference_ms=data.get("inference_ms"),
            )
            results.append(result)
            print(
                json.dumps(
                    {
                        "id": sample["id"],
                        "region": sample["region"],
                        "wer": result["word_errors"] / result["words"],
                    }
                ),
                flush=True,
            )
    groups = {}
    for region in ["North", "Central", "South"]:
        rows = [r for r in results if r["region"] == region]
        groups[region] = {
            "samples": len(rows),
            "wer": sum(r["word_errors"] for r in rows) / sum(r["words"] for r in rows),
            "cer": sum(r["character_errors"] for r in rows)
            / sum(r["characters"] for r in rows),
            "max_http_ms": max(r["http_ms"] for r in rows),
        }
    report = {k: v for k, v in manifest.items() if k != "samples"}
    report.update(
        groups=groups,
        results=results,
        limitations="3 clips per region, broadcaster/read speech; source-provided labels, not representative of population, shopping or TC2 utterance. No source audio/transcript redistributed.",
    )
    (ROOT / "docs/evidence/regional-voice.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )


if __name__ == "__main__":
    main()
