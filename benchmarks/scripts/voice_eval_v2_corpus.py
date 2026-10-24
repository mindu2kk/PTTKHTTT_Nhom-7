"""Freeze utterance-disjoint V2 before decoder ablation; existing corpora only."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from voice_eval_corpus import (
    ARCHIVES,
    PRIVATE as V1_PRIVATE,
    PUBLIC,
    ROOT,
    duration,
    sha,
    verify as verify_v1,
    write_json,
)
from voice_eval_metrics import normalize

PRIVATE = V1_PRIVATE / "v2"
MANIFEST = PRIVATE / "evaluation-v2-manifest.json"
PUBLIC_MANIFEST = PUBLIC / "evaluation-v2-manifest.json"


def choose(rows, count):
    """Prefer one per source speaker, then fill in original order, without ASR."""
    if count <= 0:
        return []
    selected, speakers = [], set()
    for row in rows:
        if row["speaker_id"] not in speakers:
            selected.append(row)
            speakers.add(row["speaker_id"])
            if len(selected) == count:
                return selected
    selected_ids = {row["id"] for row in selected}
    for row in rows:
        if row["id"] not in selected_ids:
            selected.append(row)
            if len(selected) == count:
                break
    return selected


def freeze():
    import pyarrow.parquet as pq

    verify_v1()
    if MANIFEST.exists() or PUBLIC_MANIFEST.exists():
        raise RuntimeError("V2 already frozen; never overwrite")
    original_path = V1_PRIVATE / "evaluation-manifest.json"
    original = json.loads(original_path.read_text("utf8"))
    forbidden = {r["sha256"] for r in original["samples"]}
    forbidden_text = {normalize(r["reference"]) for r in original["samples"]}
    eligible = {}
    for corpus, (relative, expected) in ARCHIVES.items():
        with (ROOT / relative).open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                raise RuntimeError("Original archive changed")
        candidates = []
        for batch in pq.ParquetFile(ROOT / relative).iter_batches(batch_size=1):
            source = batch.to_pylist()[0]
            raw = source["audio"]["bytes"]
            digest, seconds = sha(raw), duration(raw)
            reference = source["sentence"] if corpus == "vivos" else source["text"]
            if (
                digest in forbidden
                or normalize(reference) in forbidden_text
                or not normalize(reference)
                or not 1 <= seconds <= 12
                or len(raw) > 2 * 1024 * 1024
            ):
                continue
            identifier = Path(
                source["path"] if corpus == "vivos" else source["filename"]
            ).stem
            candidates.append(
                {
                    "id": f"{corpus}:{identifier}",
                    "corpus": corpus,
                    "split": "validation_v2",
                    "speaker_id": f"{corpus}:{source['speaker_id'] if corpus == 'vivos' else source['speakerID']}",
                    "sha256": digest,
                    "reference": reference,
                    "duration_seconds": seconds,
                    "region": source.get("region"),
                    "raw": raw,
                }
            )
        eligible[corpus] = candidates
    # Balanced15/14 when possible; shortage is filled by the other corpus.
    counts = {
        "vivos": min(15, len(eligible["vivos"])),
        "vimd": min(14, len(eligible["vimd"])),
    }
    for corpus in ["vivos", "vimd"]:
        counts[corpus] += min(
            29 - sum(counts.values()), len(eligible[corpus]) - counts[corpus]
        )
    selected = [
        row
        for corpus in ["vivos", "vimd"]
        for row in choose(eligible[corpus], counts[corpus])
    ]
    if not selected:
        raise RuntimeError("No eligible unseen utterances")
    PRIVATE.mkdir(parents=True, exist_ok=True)
    rows = []
    seen_sha = set()
    for sample in selected:
        raw = sample.pop("raw")
        if sample["sha256"] in seen_sha:
            raise RuntimeError("Duplicate source audio in selected V2")
        seen_sha.add(sample["sha256"])
        file = PRIVATE / (sample["id"].replace(":", "-") + ".wav")
        file.write_bytes(raw)
        rows.append({**sample, "path": file.relative_to(ROOT).as_posix()})
    manifest = {
        "version": 2,
        "frozen_at": datetime.now(UTC).isoformat(),
        "v1_manifest_sha256": sha(original_path.read_bytes()),
        "archives": ARCHIVES,
        "selection": "Before compatibility ablation/selected configuration: exclude every V1 audio SHA and normalized reference; eligible original WAV1..12s<=2MiB; stable parquet order, first eligible per speaker then source-order fill; target15 VIVOS+14 ViMD, shortage filled by other corpus. No hypotheses used.",
        "eligible_counts": {corpus: len(rows) for corpus, rows in eligible.items()},
        "rights": original["rights"],
        "warmup": original["samples"][0],
        "limitations": "Utterance-disjoint only; speakers can overlap development/V1 and each other. Not speaker-independent or upstream training holdout proof. Read/broadcast speech, not shopping/TC2/microphone proof. Warmup intentionally reuses a development clip and is not scored.",
        "samples": rows,
    }
    write_json(MANIFEST, manifest)
    public = {
        **manifest,
        "private_manifest_sha256": sha(MANIFEST.read_bytes()),
        "warmup": {
            k: v
            for k, v in manifest["warmup"].items()
            if k not in {"reference", "path"}
        },
        "samples": [
            {k: v for k, v in row.items() if k not in {"reference", "path"}}
            for row in rows
        ],
    }
    write_json(PUBLIC_MANIFEST, public)
    return verify()


def verify():
    manifest = json.loads(MANIFEST.read_text("utf8"))
    public = json.loads(PUBLIC_MANIFEST.read_text("utf8"))
    v1_path = V1_PRIVATE / "evaluation-manifest.json"
    if (
        sha(MANIFEST.read_bytes()) != public["private_manifest_sha256"]
        or sha(v1_path.read_bytes()) != manifest["v1_manifest_sha256"]
    ):
        raise RuntimeError("Frozen manifest changed")
    original = json.loads(v1_path.read_text("utf8"))
    forbidden = {row["sha256"] for row in original["samples"]}
    forbidden_text = {normalize(row["reference"]) for row in original["samples"]}
    for row in manifest["samples"]:
        if (
            sha((ROOT / row["path"]).read_bytes()) != row["sha256"]
            or row["sha256"] in forbidden
            or normalize(row["reference"]) in forbidden_text
        ):
            raise RuntimeError("Audio changed or V2 overlaps V1")
    return {
        "samples": len(manifest["samples"]),
        "speaker_ids": len({r["speaker_id"] for r in manifest["samples"]}),
        "speaker_independent": False,
        "corpora": {
            corpus: sum(r["corpus"] == corpus for r in manifest["samples"])
            for corpus in ARCHIVES
        },
        "private_manifest_sha256": sha(MANIFEST.read_bytes()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "verify"])
    args = parser.parse_args()
    print(json.dumps(freeze() if args.action == "freeze" else verify()))
