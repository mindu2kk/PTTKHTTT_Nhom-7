import hashlib
import io
import runpy
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts/download_phowhisper.py"


def test_model_download_requires_explicit_consent(monkeypatch):
    module = runpy.run_path(str(SCRIPT))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    with pytest.raises(SystemExit) as error:
        module["main"]()
    assert error.value.code == 2


def test_download_checks_hash_before_finalizing(tmp_path, monkeypatch):
    module = runpy.run_path(str(SCRIPT))
    monkeypatch.setattr("urllib.request.urlopen", lambda *args, **kwargs: io.BytesIO(b"test bytes"))
    expected = hashlib.sha256(b"test bytes").hexdigest()
    result = module["download"](tmp_path, "model.bin", "https://unused.invalid", expected)
    assert result["sha256"] == expected and (tmp_path / "model.bin").read_bytes() == b"test bytes"
    with pytest.raises(RuntimeError, match="Checksum mismatch"):
        module["download"](tmp_path, "bad.bin", "https://unused.invalid", "0" * 64)
    assert not (tmp_path / "bad.bin").exists()


def test_existing_model_with_wrong_hash_is_not_overwritten(tmp_path):
    module = runpy.run_path(str(SCRIPT))
    (tmp_path / "model.bin").write_bytes(b"existing local data")
    with pytest.raises(RuntimeError, match="not overwritten"):
        module["download"](tmp_path, "model.bin", "https://unused.invalid", "0" * 64)
    assert (tmp_path / "model.bin").read_bytes() == b"existing local data"
