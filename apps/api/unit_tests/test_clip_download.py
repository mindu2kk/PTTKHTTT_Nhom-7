import hashlib
import runpy
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/download_models.py"


def test_clip_download_needs_explicit_consent(monkeypatch):
    module = runpy.run_path(str(SCRIPT))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--only", "clip"])
    monkeypatch.setattr(
        "urllib.request.urlretrieve", lambda *args: pytest.fail("No download without consent")
    )
    with pytest.raises(SystemExit) as error:
        module["main"]()
    assert error.value.code == 2


def test_download_verifies_partial_before_finalizing_and_reuses_existing_file(
    tmp_path, monkeypatch
):
    module = runpy.run_path(str(SCRIPT))
    content = b"local model test"
    expected = hashlib.sha256(content).hexdigest()
    monkeypatch.setattr("urllib.request.urlretrieve", lambda url, path: path.write_bytes(content))
    path = tmp_path / "model.bin"
    assert module["download_file"](path, "https://unused.invalid", expected) == expected
    assert path.read_bytes() == content
    monkeypatch.setattr(
        "urllib.request.urlretrieve", lambda *args: pytest.fail("Do not redownload")
    )
    assert module["download_file"](path, "https://unused.invalid", expected) == expected


def test_bad_download_and_bad_existing_file_are_not_promoted_or_overwritten(tmp_path, monkeypatch):
    module = runpy.run_path(str(SCRIPT))
    monkeypatch.setattr("urllib.request.urlretrieve", lambda url, path: path.write_bytes(b"wrong"))
    path = tmp_path / "model.bin"
    with pytest.raises(ValueError, match="Checksum mismatch"):
        module["download_file"](path, "https://unused.invalid", "0" * 64)
    assert not path.exists()
    assert path.with_suffix(".bin.partial").exists()
    path.write_bytes(b"existing data")
    with pytest.raises(ValueError, match="Checksum mismatch"):
        module["download_file"](path, "https://unused.invalid", "0" * 64)
    assert path.read_bytes() == b"existing data"
