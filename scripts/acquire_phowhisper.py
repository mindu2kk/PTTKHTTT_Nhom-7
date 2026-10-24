"""Explicitly consented model acquisition, pinned official files; never called by search."""

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
REPO = "vinai/PhoWhisper-base"
REVISION = "7ebdb9e88f5cc5271fb88f4d642c82ff9388650e"
WEIGHT_HASH = "910b9e8875497078efa83dc506ea7ee378e4e759a206ceecbf23e088aec9b9f8"
NAMES = (
    "README.md",
    "added_tokens.json",
    "config.json",
    "generation_config.json",
    "merges.txt",
    "normalizer.json",
    "preprocessor_config.json",
    "pytorch_model.bin",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
)


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consented", action="store_true")
    args = parser.parse_args()
    if not args.consented:
        parser.error("Cần đồng ý rõ trước khi tải model; không tải tự động.")
    target = ROOT / "models/phowhisper-base-source"
    target.mkdir(parents=True, exist_ok=True)
    records = []
    with httpx.Client(follow_redirects=True, timeout=90, trust_env=False) as client:
        metadata = client.get(
            f"https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true"
        )
        metadata.raise_for_status()
        data = metadata.json()
        assert data["sha"] == REVISION and data["cardData"]["license"] == "bsd-3-clause"
        files = {s["rfilename"]: s for s in data["siblings"]}
        for name in NAMES:
            source = files[name]
            path = target / name
            if not path.exists():
                print(f"Downloading {name}: {source['size']} bytes", flush=True)
                temporary = path.with_suffix(path.suffix + ".partial")
                with client.stream(
                    "GET", f"https://huggingface.co/{REPO}/resolve/{REVISION}/{name}"
                ) as response:
                    response.raise_for_status()
                    with temporary.open("wb") as output:
                        for chunk in response.iter_bytes(1024 * 1024):
                            output.write(chunk)
                assert temporary.stat().st_size == source["size"], name
                actual = digest(temporary)
                expected = source.get("lfs", {}).get("sha256")
                assert not expected or actual == expected, name
                if name == "pytorch_model.bin":
                    assert actual == WEIGHT_HASH
                temporary.replace(path)
            actual = digest(path)
            assert path.stat().st_size == source["size"]
            if name == "pytorch_model.bin":
                assert actual == WEIGHT_HASH
            records.append(
                {"file": name, "bytes": path.stat().st_size, "sha256": actual}
            )
        license_url = (
            "https://raw.githubusercontent.com/VinAIResearch/PhoWhisper/main/LICENSE"
        )
        license_response = client.get(license_url)
        license_response.raise_for_status()
        (target / "LICENSE").write_bytes(license_response.content)
    manifest = {
        "source": REPO,
        "revision": REVISION,
        "license": "BSD-3-Clause",
        "license_url": license_url,
        "license_sha256": digest(target / "LICENSE"),
        "consent": "User explicitly approved download and local testing in chat on 2026-10-23",
        "acquired_at": datetime.now(UTC).isoformat(),
        "files": records,
        "download_bytes": sum(r["bytes"] for r in records),
        "runtime_network_inference": False,
    }
    report = json.dumps(manifest, ensure_ascii=False, indent=2)
    (target / "acquisition-manifest.json").write_text(report, "utf8")
    evidence = ROOT / "docs/evidence/voice-upgrade"
    evidence.mkdir(parents=True, exist_ok=True)
    (evidence / "model-acquisition.json").write_text(report, "utf8")
    print(
        f"Verified {len(records)} files, {manifest['download_bytes']} bytes. Not yet a quality claim."
    )


if __name__ == "__main__":
    main()
