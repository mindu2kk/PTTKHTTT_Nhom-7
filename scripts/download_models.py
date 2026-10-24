"""One-time downloads explicitly approved by the user on 2026-10-21. No inference API."""

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "models"
SOURCES = {
    "clip": (
        "laion/CLIP-ViT-B-32-laion2B-s34B-b79K",
        "1a25a446712ba5ee05982a381eed697ef9b435cf",
        ["open_clip_model.safetensors", "open_clip_config.json"],
    ),
    "whisper": (
        "Systran/faster-whisper-base",
        "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66",
        ["model.bin", "config.json", "tokenizer.json", "vocabulary.txt"],
    ),
}


def main() -> None:
    manifest = []
    for folder, (repo, revision, names) in SOURCES.items():
        target = ROOT / folder
        target.mkdir(parents=True, exist_ok=True)
        for name in names:
            path = target / name
            if not path.exists():
                url = f"https://huggingface.co/{repo}/resolve/{revision}/{name}"
                temporary = path.with_suffix(path.suffix + ".partial")
                print(f"Downloading {folder}/{name}", flush=True)
                urllib.request.urlretrieve(url, temporary)
                temporary.replace(path)
            manifest.append(
                dict(
                    repo=repo,
                    revision=revision,
                    file=f"{folder}/{name}",
                    bytes=path.stat().st_size,
                    sha256=hashlib.file_digest(path.open("rb"), "sha256").hexdigest(),
                    license="MIT",
                    consent="user 2026-10-21",
                )
            )
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    evidence = ROOT.parent / "docs/evidence/model-manifest.json"
    evidence.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print("Model files downloaded; no inference claims until actual integration tests.")


if __name__ == "__main__":
    main()
