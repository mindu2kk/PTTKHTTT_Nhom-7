"""Explicit one-time PhoWhisper acquisition; never called by application startup."""

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

REVISION = "7ebdb9e88f5cc5271fb88f4d642c82ff9388650e"
WEIGHT_HASH = "910b9e8875497078efa83dc506ea7ee378e4e759a206ceecbf23e088aec9b9f8"
LICENSE_HASH = "6ba6977f0a21f70170fac152bb5d7ef9c136ee708007f49efb9a8729883b60cd"
FILES = (
    "config.json",
    "generation_config.json",
    "preprocessor_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "added_tokens.json",
    "merges.txt",
    "normalizer.json",
    "vocab.json",
    "README.md",
    "pytorch_model.bin",
)


def download(
    target: Path, name: str, url: str, expected: str | None = None
) -> dict[str, str | int]:
    path = target / name
    if not path.exists():
        partial = path.with_suffix(path.suffix + ".partial")
        print(f"Downloading {name}", flush=True)
        with (
            urllib.request.urlopen(url, timeout=60) as response,
            partial.open("wb") as output,
        ):
            while block := response.read(1024 * 1024):
                output.write(block)
        with partial.open("rb") as source:
            checksum = hashlib.file_digest(source, "sha256").hexdigest()
        if expected and checksum != expected:
            raise RuntimeError(
                f"Checksum mismatch: {name}; partial file retained for inspection"
            )
        partial.replace(path)
    with path.open("rb") as source:
        checksum = hashlib.file_digest(source, "sha256").hexdigest()
    if expected and checksum != expected:
        raise RuntimeError(f"Existing {name} has unexpected checksum; not overwritten")
    return {"file": name, "bytes": path.stat().st_size, "sha256": checksum}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--consent", action="store_true", help="Explicitly accept this model download"
    )
    if not parser.parse_args().consent:
        parser.error(
            "Model weights require explicit consent; use --consent after reviewing the source"
        )
    target = Path(__file__).resolve().parents[1] / "models" / "phowhisper-base-source"
    target.mkdir(parents=True, exist_ok=True)
    files = [
        download(
            target,
            name,
            f"https://huggingface.co/vinai/PhoWhisper-base/resolve/{REVISION}/{name}",
            WEIGHT_HASH if name == "pytorch_model.bin" else None,
        )
        for name in FILES
    ]
    files.append(
        download(
            target,
            "LICENSE",
            "https://raw.githubusercontent.com/VinAIResearch/PhoWhisper/main/LICENSE",
            LICENSE_HASH,
        )
    )
    (target / "acquisition.json").write_text(
        json.dumps(
            {
                "source": "vinai/PhoWhisper-base",
                "revision": REVISION,
                "license": "BSD-3-Clause",
                "explicit_consent": True,
                "files": files,
            },
            indent=2,
        )
        + "\n",
        encoding="utf8",
    )
    print(f"Verified model source: {target}")


if __name__ == "__main__":
    main()
