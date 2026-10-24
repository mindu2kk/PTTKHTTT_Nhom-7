"""Rights-reviewed MIT Fashion-MNIST product-thumbnail holdout, independent of demo artwork."""

import gzip
import hashlib
import io
import json
import math
import urllib.request
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data/private/fashion-mnist"
STORE.mkdir(parents=True, exist_ok=True)
FILES = {
    "train-images-idx3-ubyte.gz": "8d4fb7e6c68d591d4c3dfef9ec88bf0d",
    "train-labels-idx1-ubyte.gz": "25c81989df183df01b3e8a0aad5dffbe",
    "t10k-images-idx3-ubyte.gz": "bef4ecab320f06d8554ea6380940ec79",
    "t10k-labels-idx1-ubyte.gz": "bb300cfdad3c16e7a12a480ee83cd310",
}


def sample(prefix, count_per_label):
    images = gzip.decompress((STORE / f"{prefix}-images-idx3-ubyte.gz").read_bytes())[
        16:
    ]
    labels = gzip.decompress((STORE / f"{prefix}-labels-idx1-ubyte.gz").read_bytes())[
        8:
    ]
    counts = {i: 0 for i in range(10)}
    result = []
    for i, label in enumerate(labels):
        if counts[label] >= count_per_label:
            continue
        image = Image.frombytes("L", (28, 28), images[i * 784 : (i + 1) * 784]).convert(
            "RGB"
        )
        image = image.resize((224, 224), Image.Resampling.BICUBIC)
        buffer = io.BytesIO()
        image.save(buffer, "PNG")
        result.append((f"{prefix}-{i}", label, buffer.getvalue()))
        counts[label] += 1
        if len(result) == 10 * count_per_label:
            break
    return result


def main():
    for name, expected in FILES.items():
        target = STORE / name
        if not target.exists():
            print(f"Downloading licensed benchmark {name}", flush=True)
            urllib.request.urlretrieve(
                f"https://raw.githubusercontent.com/zalandoresearch/fashion-mnist/master/data/fashion/{name}",
                target,
            )
        assert hashlib.md5(target.read_bytes()).hexdigest() == expected
    license_url = (
        "https://raw.githubusercontent.com/zalandoresearch/fashion-mnist/master/LICENSE"
    )
    (STORE / "LICENSE").write_bytes(urllib.request.urlopen(license_url).read())
    manifest = {
        "source": "https://github.com/zalandoresearch/fashion-mnist",
        "license": "MIT",
        "copyright": "Copyright 2017 Zalando SE",
        "license_url": license_url,
        "purpose": "local research benchmark only; no merchant facts/price inferred",
        "suitability": "28x28 grayscale product thumbnails; not smartphone photos; no color evaluation",
        "files": [{"name": name, "md5": checksum} for name, checksum in FILES.items()],
    }
    gallery = sample("train", 10)
    queries = sample("t10k", 2)
    vectors = {}
    timings = []
    with httpx.Client(
        base_url="http://localhost:19090", timeout=60, trust_env=False
    ) as client:
        for i, (identifier, label, raw) in enumerate([*gallery, *queries]):
            response = client.post(
                "/encode", content=raw, headers={"Content-Type": "image/png"}
            )
            response.raise_for_status()
            data = response.json()
            vectors[identifier] = data["vector"]
            timings.append(data["inference_ms"])
            if i % 20 == 0:
                print(f"Encoded benchmark {i + 1}/120", flush=True)
    metrics = {f"hit@{k}": [] for k in [1, 5, 10]}
    metrics.update({f"recall@{k}": [] for k in [1, 5, 10]})
    ndcg = []
    failures = []
    for identifier, label, _ in queries:
        q = vectors[identifier]
        ranked = sorted(
            gallery,
            key=lambda g: -sum(a * b for a, b in zip(q, vectors[g[0]], strict=True)),
        )
        for k in [1, 5, 10]:
            correct = sum(row[1] == label for row in ranked[:k])
            metrics[f"hit@{k}"].append(float(correct > 0))
            metrics[f"recall@{k}"].append(correct / 10)
        dcg = sum(
            (row[1] == label) / math.log2(i + 2) for i, row in enumerate(ranked[:10])
        )
        ndcg.append(dcg / sum(1 / math.log2(i + 2) for i in range(10)))
        if ranked[0][1] != label:
            failures.append(
                {"id": identifier, "expected_label": label, "top1_label": ranked[0][1]}
            )
    result = {
        "manifest": manifest,
        "gallery": 100,
        "held_out_queries": 20,
        "balanced_labels": 10,
        "qrels": "Zalando class labels; relevant iff gallery/query share class; train/test IDs disjoint",
        "metrics": {
            key: round(sum(values) / len(values), 4) for key, values in metrics.items()
        },
        "ndcg@10": round(sum(ndcg) / len(ndcg), 4),
        "failure_examples": failures,
        "inference_p95_ms": round(sorted(timings[100:])[18], 3),
        "limits": "Thumbnail transfer benchmark, not end-to-end store retrieval or smartphone robustness; class labels do not identify the same product",
    }
    (ROOT / "docs/evidence/fashion-mnist-eval.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
