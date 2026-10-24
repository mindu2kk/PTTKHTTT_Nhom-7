"""Explicit local ASR profiles; a missing optional model never downloads or falls back."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

PHOWHISPER_SOURCE_SHA256 = (
    "910b9e8875497078efa83dc506ea7ee378e4e759a206ceecbf23e088aec9b9f8"
)


@dataclass(frozen=True)
class ASRProfile:
    key: str
    directory: str
    recognizer: str
    revision: str
    without_timestamps: bool = False

    def path(self, root: Path) -> Path:
        return root / self.directory

    def validate_for_load(self, root: Path) -> Path:
        """Hash once before loading the optional converted model, never per request."""
        local = self.path(root)
        if self.key != "phowhisper-base":
            return local
        try:
            manifest_path = local / "conversion-manifest.json"
            if manifest_path.stat().st_size > 65536:
                raise ValueError("Manifest quá lớn.")
            manifest = json.loads(manifest_path.read_text("utf8"))
            if not isinstance(manifest, dict) or any(
                manifest.get(key) != expected
                for key, expected in {
                    "source": "vinai/PhoWhisper-base",
                    "source_revision": self.revision,
                    "source_weight_sha256": PHOWHISPER_SOURCE_SHA256,
                    "quantization": "int8",
                    "local_conversion": True,
                }.items()
            ):
                raise ValueError("Nguồn hoặc định dạng mô hình không khớp.")
            files = manifest.get("files")
            if not isinstance(files, list) or not 4 <= len(files) <= 32:
                raise ValueError("Danh sách tệp không hợp lệ.")
            names = set()
            for record in files:
                if not isinstance(record, dict):
                    raise ValueError("Bản ghi tệp không hợp lệ.")
                name, size, expected = (
                    record.get("file"),
                    record.get("bytes"),
                    record.get("sha256"),
                )
                if (
                    not isinstance(name, str)
                    or not re.fullmatch(r"[A-Za-z0-9_.-]+", name)
                    or name in {".", "..", "conversion-manifest.json"}
                    or name in names
                    or type(size) is not int
                    or size <= 0
                    or not isinstance(expected, str)
                    or not re.fullmatch(r"[0-9a-f]{64}", expected)
                ):
                    raise ValueError("Tên, kích thước hoặc SHA256 không hợp lệ.")
                names.add(name)
                path = local / name
                if path.is_symlink() or path.stat().st_size != size:
                    raise ValueError("Tệp mô hình đã thay đổi.")
                digest = hashlib.sha256()
                with path.open("rb") as source:
                    for block in iter(lambda: source.read(1024 * 1024), b""):
                        digest.update(block)
                if digest.hexdigest() != expected:
                    raise ValueError("SHA256 mô hình không khớp.")
            if (
                not {
                    "model.bin",
                    "config.json",
                    "tokenizer.json",
                    "preprocessor_config.json",
                }
                <= names
            ):
                raise ValueError("Thiếu tệp mô hình bắt buộc.")
            actual = {
                p.name for p in local.iterdir() if p.name != "conversion-manifest.json"
            }
            if actual != names:
                raise ValueError("Thư mục có tệp chưa xác minh.")
        except (OSError, UnicodeError, ValueError, TypeError) as error:
            raise ValueError(
                "Mô hình PhoWhisper cục bộ chưa vượt kiểm tra toàn vẹn."
            ) from error
        return local


PROFILES = {
    "whisper-base": ASRProfile(
        "whisper-base",
        "whisper",
        "faster-whisper base int8 CPU",
        "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66",
    ),
    "phowhisper-base": ASRProfile(
        "phowhisper-base",
        "phowhisper-base-int8",
        "PhoWhisper base int8 CPU",
        "7ebdb9e88f5cc5271fb88f4d642c82ff9388650e",
        without_timestamps=True,
    ),
}


def get_profile(name: str = "whisper-base") -> ASRProfile:
    if name not in PROFILES:
        raise ValueError("ASR_MODEL_PROFILE không nằm trong danh sách mô hình cục bộ.")
    return PROFILES[name]
