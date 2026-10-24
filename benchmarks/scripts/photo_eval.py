"""CaltechDATA CC-BY-4.0 product-object photo holdout; never public store data."""

import hashlib
import io
import json
import math
import tarfile
import zipfile
from pathlib import Path

import httpx
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data/private/caltech101"
URL = "https://data.caltech.edu/records/mzrjq-6wc02/files/caltech-101.zip?download=1"
MD5 = "3138e1922a9193bfa496528edbbc45d0"
LABELS = ["camera", "headphone", "laptop", "watch", "umbrella"]


def prepare():
    STORE.mkdir(parents=True, exist_ok=True)
    archive = STORE / "caltech-101.zip"
    if not archive.exists():
        with httpx.stream("GET", URL, follow_redirects=True, timeout=90) as response:
            response.raise_for_status()
            with archive.with_suffix(".partial").open("wb") as output:
                for chunk in response.iter_bytes(1024 * 1024):
                    output.write(chunk)
        archive.with_suffix(".partial").replace(archive)
    with archive.open("rb") as source:
        if hashlib.file_digest(source, "md5").hexdigest() != MD5:
            raise RuntimeError("Caltech archive hash changed; review source")
    samples = []
    with (
        zipfile.ZipFile(archive) as zipped,
        tarfile.open(
            fileobj=io.BytesIO(zipped.read("caltech-101/101_ObjectCategories.tar.gz")),
            mode="r:gz",
        ) as tar,
    ):
        members = sorted(
            (
                m
                for m in tar.getmembers()
                if m.isfile() and Path(m.name).suffix == ".jpg"
            ),
            key=lambda m: m.name,
        )
        for label in LABELS:
            chosen = [m for m in members if Path(m.name).parent.name == label][:15]
            assert len(chosen) == 15
            for index, member in enumerate(chosen):
                source = tar.extractfile(member)
                assert source is not None
                raw = source.read()
                image = Image.open(io.BytesIO(raw)).convert("RGB")
                image.thumbnail((640, 640))
                output = io.BytesIO()
                image.save(output, format="PNG")
                identifier = label + "-" + Path(member.name).stem
                samples.append(
                    {
                        "id": identifier,
                        "label": label,
                        "split": "gallery" if index < 10 else "query",
                        "archive_path": member.name,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "raw": output.getvalue(),
                    }
                )
    manifest = {
        "source": "https://data.caltech.edu/records/mzrjq-6wc02",
        "url": URL,
        "archive_md5": MD5,
        "license": "CC-BY-4.0",
        "authors": [
            "Fei-Fei Li",
            "Marco Andreetto",
            "Marc Aurelio Ranzato",
            "Pietro Perona",
        ],
        "use": "Academic private benchmark; no public store import",
        "selection": "First 15 sorted files per chosen object class, first10 gallery/last5 query; exact bytes/IDs disjoint",
        "samples": [{k: v for k, v in s.items() if k != "raw"} for s in samples],
    }
    (STORE / "selection.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf8"
    )
    return samples, manifest


def main():
    samples, manifest = prepare()
    gallery = [s for s in samples if s["split"] == "gallery"]
    queries = [s for s in samples if s["split"] == "query"]
    sheet = Image.new("RGB", (5 * 200, 5 * 170), "white")
    draw = ImageDraw.Draw(sheet)
    for i, sample in enumerate(queries):
        image = Image.open(io.BytesIO(sample["raw"]))
        image.thumbnail((195, 140))
        x, y = (i % 5) * 200, (i // 5) * 170
        sheet.paste(image, (x, y))
        draw.text((x, y + 142), sample["id"], fill="black")
    sheet.save(STORE / "query-contact-sheet.png")
    vectors = {}
    timings = []
    with httpx.Client(
        base_url="http://localhost:19090", timeout=65, trust_env=False
    ) as client:
        for sample in samples:
            response = client.post(
                "/encode", content=sample["raw"], headers={"Content-Type": "image/png"}
            )
            response.raise_for_status()
            data = response.json()
            vectors[sample["id"]] = data["vector"]
            if sample["split"] == "query":
                timings.append(data["inference_ms"])
    results = []
    for sample in queries:
        vector = vectors[sample["id"]]
        ranked = sorted(
            gallery,
            key=lambda g: (
                -sum(a * b for a, b in zip(vector, vectors[g["id"]], strict=True)),
                g["id"],
            ),
        )
        relevance = [int(g["label"] == sample["label"]) for g in ranked]
        dcg = sum(rel / math.log2(i + 2) for i, rel in enumerate(relevance[:10]))
        results.append(
            {
                "id": sample["id"],
                "label": sample["label"],
                "top10": [g["id"] for g in ranked[:10]],
                "hit1": relevance[0],
                "hit5": int(any(relevance[:5])),
                "hit10": int(any(relevance[:10])),
                "precision10": sum(relevance[:10]) / 10,
                "recall10": sum(relevance[:10]) / 10,
                "ndcg10": dcg / sum(1 / math.log2(i + 2) for i in range(10)),
            }
        )
    report = {
        "manifest": manifest,
        "gallery": len(gallery),
        "held_out_queries": len(queries),
        "qrels": "Original Caltech class labels; all10 gallery objects of same class relevant. Not same-SKU identity.",
        "metrics": {
            key: round(sum(r[key] for r in results) / len(results), 4)
            for key in ["hit1", "hit5", "hit10", "precision10", "recall10", "ndcg10"]
        },
        "uncached_encoder_p95_ms": round(
            sorted(timings)[math.ceil(len(timings) * 0.95) - 1], 3
        ),
        "queries": results,
        "limitations": "Small natural object-image benchmark; not smartphone capture study, not fashion same-product retrieval, no camera-photo catalogue provenance claims.",
    }
    (ROOT / "docs/evidence/photo-eval.json").write_text(
        json.dumps(report, indent=2), encoding="utf8"
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k not in ["manifest", "queries"]},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
