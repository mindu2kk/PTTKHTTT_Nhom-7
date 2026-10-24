"""V2 selector and configuration guards; no model/database/network."""

import importlib
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
corpus = importlib.import_module("voice_eval_v2_corpus")
runner = importlib.import_module("voice_eval_v2_run")


def test_zero_quota_does_not_select_an_entire_corpus():
    assert corpus.choose([{"id": "a", "speaker_id": "s1"}], 0) == []


def test_stable_speaker_first_order_and_remainder():
    rows = [
        {"id": "a1", "speaker_id": "a"},
        {"id": "a2", "speaker_id": "a"},
        {"id": "b1", "speaker_id": "b"},
        {"id": "c1", "speaker_id": "c"},
    ]
    assert [r["id"] for r in corpus.choose(rows, 4)] == ["a1", "b1", "c1", "a2"]
    assert [r["id"] for r in corpus.choose(rows, 2)] == ["a1", "b1"]
    assert [r["id"] for r in rows] == ["a1", "a2", "b1", "c1"]


def test_empty_source_returns_empty():
    assert corpus.choose([], 5) == []


def test_run_refuses_to_decode_before_configuration_lock(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "verify", lambda: None)
    monkeypatch.setattr(runner, "LOCK", tmp_path / "no-lock.json")
    with pytest.raises(RuntimeError, match="Lock the development configuration"):
        runner.run(Namespace())


def test_configuration_cannot_use_heldout_as_development(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "verify", lambda: None)
    monkeypatch.setattr(runner, "LOCK", tmp_path / "lock.json")
    evidence = tmp_path / "heldout.json"
    evidence.write_text(json.dumps({"split": "heldout"}), encoding="utf8")
    with pytest.raises(ValueError, match="development evidence"):
        runner.lock_configuration(Namespace(development_evidence=evidence))


def test_existing_configuration_lock_is_immutable(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "verify", lambda: None)
    lock = tmp_path / "lock.json"
    lock.write_text("{}", encoding="utf8")
    monkeypatch.setattr(runner, "LOCK", lock)
    with pytest.raises(RuntimeError, match="already locked"):
        runner.lock_configuration(Namespace())
