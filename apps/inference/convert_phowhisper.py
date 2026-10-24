"""Convert an already consented, verified local PhoWhisper snapshot; never downloads."""

import argparse
import hashlib
import json
import os
from pathlib import Path

SOURCE_REVISION = "7ebdb9e88f5cc5271fb88f4d642c82ff9388650e"
SOURCE_WEIGHT_SHA256 = (
    "910b9e8875497078efa83dc506ea7ee378e4e759a206ceecbf23e088aec9b9f8"
)


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if not source.is_dir() or output.exists():
        parser.error("Source phải tồn tại và output phải là thư mục mới.")
    if sha256(source / "pytorch_model.bin") != SOURCE_WEIGHT_SHA256:
        parser.error("SHA256 checkpoint không khớp revision đã duyệt.")
    for name in ("config.json", "tokenizer.json", "preprocessor_config.json"):
        if not (source / name).is_file():
            parser.error(f"Thiếu tệp cục bộ: {name}")

    os.environ.update(
        HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false"
    )
    import importlib.metadata

    from ctranslate2.converters import TransformersConverter

    class SafeLocalConverter(TransformersConverter):
        def load_model(self, model_class, model_name_or_path, **kwargs):
            kwargs.update(
                weights_only=True,
                local_files_only=True,
                trust_remote_code=False,
                use_safetensors=False,
            )
            return super().load_model(model_class, model_name_or_path, **kwargs)

        def load_tokenizer(self, tokenizer_class, model_name_or_path, **kwargs):
            kwargs.update(local_files_only=True, trust_remote_code=False)
            return super().load_tokenizer(tokenizer_class, model_name_or_path, **kwargs)

    SafeLocalConverter(
        str(source),
        copy_files=[
            "tokenizer.json",
            "preprocessor_config.json",
            "LICENSE",
            "README.md",
        ],
        trust_remote_code=False,
    ).convert(str(output), quantization="int8")
    manifest = {
        "source": "vinai/PhoWhisper-base",
        "source_revision": SOURCE_REVISION,
        "source_weight_sha256": SOURCE_WEIGHT_SHA256,
        "license": "BSD-3-Clause",
        "quantization": "int8",
        "local_conversion": True,
        "tool_versions": {
            name: importlib.metadata.version(name)
            for name in ("ctranslate2", "transformers", "torch")
        },
        "files": [
            {"file": p.name, "bytes": p.stat().st_size, "sha256": sha256(p)}
            for p in sorted(output.iterdir())
            if p.is_file()
        ],
    }
    (output / "conversion-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), "utf8"
    )
    print(json.dumps({"output": str(output), "files": len(manifest["files"])}))


if __name__ == "__main__":
    main()
