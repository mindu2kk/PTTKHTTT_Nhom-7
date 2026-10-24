"""Tests for benchmark validity, with no ASR/database/network."""

import importlib.util
import sys
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "voice_eval_metrics", Path(__file__).with_name("voice_eval_metrics.py")
)
metrics = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = metrics
spec.loader.exec_module(metrics)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("  TAI\tNGHE\n", "tai nghe"),
        ("đèn,bàn", "đèn bàn"),
        ("tai-nghe", "tai nghe"),
        ("500.000 đồng", "500 000 đồng"),
        ("A\u0301O", "áo"),
        ("  áo   len  ", "áo len"),
        ("đèn đen", "đèn đen"),
    ],
)
def test_primary_normalizer(source, expected):
    assert metrics.normalize(source) == expected


def test_digits_are_not_silently_converted():
    assert metrics.score("hai mươi ba", "23")["word_errors"] == 3


def test_empty_hypothesis_counts_as_deletion():
    assert metrics.score("tai nghe", "")["word_errors"] == 2


def test_wer_may_exceed_one():
    assert metrics.score("áo", "xin chào các bạn")["word_errors"] > 1


def test_empty_reference_rejected():
    with pytest.raises(ValueError):
        metrics.score("!!!", "áo")


def row(identifier, reference, hypothesis, speaker="s1"):
    return {
        "id": identifier,
        "sha256": identifier,
        "speaker_id": speaker,
        "status": 200,
        "wall_ms": 1,
        **metrics.score(reference, hypothesis),
    }


def test_corpus_wer_is_weighted_by_reference_words():
    report = metrics.summarize(
        [row("1", "áo", ""), row("2", "tôi muốn mua tai nghe", "tôi muốn mua tai nghe")]
    )
    assert report["wer"] == 1 / 6


def test_changed_audio_rejected_by_pairing():
    before = [row("1", "áo", "áo")]
    after = [{**before[0], "sha256": "changed"}]
    with pytest.raises(ValueError):
        metrics.paired_delta(before, after)


def test_paired_cluster_bootstrap_reproducible():
    before = [row("1", "áo len", "áo lông"), row("2", "tai nghe", "tay nghe", "s2")]
    after = [row("1", "áo len", "áo len"), row("2", "tai nghe", "tai nghe", "s2")]
    assert metrics.paired_delta(before, after) == metrics.paired_delta(before, after)
    assert metrics.paired_delta(before, after)["candidate_minus_baseline_wer"] == -0.5
