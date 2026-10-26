"""One-time, explicitly consented downloads. Never called by application startup."""

import argparse
import hashlib
import json
import urllib.request
from datetime import date
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


def verify_checksum(path: Path, expected: str) -> str:
    with path.open("rb") as source:
        checksum = hashlib.file_digest(source, "sha256").hexdigest()
    if checksum != expected:
        raise ValueError(
            f"Checksum mismatch: {path.name}; file retained, not overwritten"
        )
    return checksum


def download_file(path: Path, url: str, expected: str) -> str:
    if not path.exists():
        partial_path = path.with_suffix(path.suffix + ".partial")
        print(f"Downloading {path.parent.name}/{path.name}", flush=True)
        urllib.request.urlretrieve(url, partial_path)
        checksum = verify_checksum(partial_path, expected)
        partial_path.replace(path)
        return checksum
    return verify_checksum(path, expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consent", action="store_true")
    parser.add_argument("--only", choices=list(SOURCES), required=True)
    args = parser.parse_args()
    if not args.consent:
        parser.error(
            "Model download requires explicit consent; pass --consent after review"
        )

    pinned_manifest = ROOT.parent / "docs/evidence/model-manifest.json"
    pinned_files = json.loads(pinned_manifest.read_text(encoding="utf8"))
    expected_hashes = {entry["file"]: entry["sha256"] for entry in pinned_files}
    repository, revision, filenames = SOURCES[args.only]
    directory = ROOT / args.only
    directory.mkdir(parents=True, exist_ok=True)
    manifest = []
    for filename in filenames:
        relative_path = f"{args.only}/{filename}"
        path = directory / filename
        url = f"https://huggingface.co/{repository}/resolve/{revision}/{filename}"
        checksum = download_file(path, url, expected_hashes[relative_path])
        manifest.append(
            {
                "repo": repository,
                "revision": revision,
                "file": relative_path,
                "bytes": path.stat().st_size,
                "sha256": checksum,
                "license": "MIT",
                "consent": f"explicit user consent {date.today().isoformat()}",
            }
        )
    (directory / "acquisition.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf8"
    )
    print("Model files downloaded; no inference claims until actual integration tests.")


if __name__ == "__main__":
    main()
