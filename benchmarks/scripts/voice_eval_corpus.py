"""Freeze a new speaker-disjoint heldout from already-downloaded, private corpora.

No network calls, transformations, hypothesis-driven selection or overwrite.
"""

import argparse
import hashlib
import io
import json
import wave
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / "data/private/voice-upgrade"
PUBLIC = ROOT / "docs/evidence/voice-upgrade"
ARCHIVES = {
    "vivos": (
        "data/private/vivos/test.parquet",
        "c37e8fc3cf5c4e446960cfa032683d74f759b5146ac475a087e1e327b0cf5d89",
    ),
    "vimd": (
        "data/private/vimd/test-00008.parquet",
        "d617472eb2880ed1c74352381f3158cf77891694e6647f4c01dd547ce18107eb",
    ),
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )


def duration(raw):
    try:
        with wave.open(io.BytesIO(raw)) as stream:
            return stream.getnframes() / stream.getframerate()
    except (wave.Error, EOFError):
        return 0


def freeze():
    import pyarrow.parquet as pq

    destination = PRIVATE / "evaluation-manifest.json"
    if destination.exists():
        raise RuntimeError(
            "Manifest already frozen. Use verify; never silently replace heldout."
        )
    for relative, expected in ARCHIVES.values():
        with (ROOT / relative).open("rb") as source:
            if hashlib.file_digest(source, "sha256").hexdigest() != expected:
                raise RuntimeError(f"Source hash changed: {relative}")
    previous = {
        "vivos": json.loads(
            (ROOT / "data/private/vivos/samples.json").read_text("utf8")
        ),
        "vimd": json.loads(
            (ROOT / "data/private/vimd/regional-selection.json").read_text("utf8")
        )["samples"],
    }
    rows = []
    for corpus, samples in previous.items():
        for sample in samples:
            raw = (ROOT / "data/private" / corpus / sample["file"]).read_bytes()
            rows.append(
                {
                    "id": f"{corpus}:{sample['id']}",
                    "corpus": corpus,
                    "split": "development",
                    "speaker_id": f"{corpus}:{sample['speaker_id']}",
                    "reference": sample["reference"],
                    "duration_seconds": duration(raw),
                    "sha256": sha(raw),
                    "path": (Path("data/private") / corpus / sample["file"]).as_posix(),
                }
            )
    used_speakers = {r["speaker_id"] for r in rows}
    PRIVATE.mkdir(parents=True, exist_ok=True)
    for corpus, target in [("vivos", 9), ("vimd", 20)]:
        selected = {}
        # Keep first eligible utterance per previously unseen speaker in stable source order.
        for batch in pq.ParquetFile(ROOT / ARCHIVES[corpus][0]).iter_batches(
            batch_size=1
        ):
            sample = batch.to_pylist()[0]
            speaker = f"{corpus}:{sample['speaker_id'] if corpus == 'vivos' else sample['speakerID']}"
            if speaker in used_speakers or speaker in selected:
                continue
            raw = sample["audio"]["bytes"]
            seconds = duration(raw)
            reference = sample["sentence"] if corpus == "vivos" else sample["text"]
            if (
                not 1 <= seconds <= 12
                or len(raw) > 2 * 1024 * 1024
                or not reference.strip()
            ):
                continue
            identifier = Path(
                sample["path"] if corpus == "vivos" else sample["filename"]
            ).stem
            destination_audio = PRIVATE / f"{corpus}-{identifier}.wav"
            destination_audio.write_bytes(raw)
            selected[speaker] = {
                "id": f"{corpus}:{identifier}",
                "corpus": corpus,
                "split": "heldout",
                "speaker_id": speaker,
                "reference": reference,
                "duration_seconds": seconds,
                "sha256": sha(raw),
                "path": destination_audio.relative_to(ROOT).as_posix(),
                "region": sample.get("region"),
            }
            if len(selected) == target:
                break
        if len(selected) != target:
            raise RuntimeError(
                f"Only {len(selected)} eligible {corpus} speakers; requested {target}"
            )
        rows.extend(selected.values())
    manifest = {
        "version": 1,
        "frozen_at": datetime.now(UTC).isoformat(),
        "selection": "Before any new ASR runs: all29 historical development clips, then first eligible1..12s original utterance per unseen speaker in stable parquet order;9 VIVOS and20 ViMD heldout speakers. No hypothesis used.",
        "archives": ARCHIVES,
        "rights": {
            "vivos": "Luong & Vu, CC-BY-NC-SA-4.0; private academic evaluation",
            "vimd": "Nguyen Dinh et al., CC-BY-NC-ND-4.0; original bytes unmodified, private academic evaluation",
        },
        "limitations": "Read/broadcast speech, mostly South ViMD; not shopping, TC2, microphones/noise population validation. One clip per heldout speaker, not training holdout proof against upstream model training.",
        "samples": rows,
    }
    write_json(destination, manifest)
    public = {
        **manifest,
        "private_manifest_sha256": sha(destination.read_bytes()),
        "samples": [
            {k: v for k, v in row.items() if k not in {"reference", "path"}}
            for row in rows
        ],
    }
    write_json(PUBLIC / "evaluation-manifest.json", public)
    return verify()


def verify():
    path = PRIVATE / "evaluation-manifest.json"
    manifest = json.loads(path.read_text("utf8"))
    public = json.loads((PUBLIC / "evaluation-manifest.json").read_text("utf8"))
    if sha(path.read_bytes()) != public["private_manifest_sha256"]:
        raise RuntimeError("Private frozen manifest changed")
    speakers = {}
    for row in manifest["samples"]:
        if sha((ROOT / row["path"]).read_bytes()) != row["sha256"]:
            raise RuntimeError(f"Audio changed: {row['id']}")
        speakers.setdefault(row["split"], set()).add(row["speaker_id"])
    if speakers["development"] & speakers["heldout"]:
        raise RuntimeError("Speaker leakage between development and heldout")
    return {
        split: {
            "clips": sum(r["split"] == split for r in manifest["samples"]),
            "speakers": len(values),
        }
        for split, values in speakers.items()
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["freeze", "verify"])
    args = parser.parse_args()
    print(json.dumps(freeze() if args.action == "freeze" else verify()))
