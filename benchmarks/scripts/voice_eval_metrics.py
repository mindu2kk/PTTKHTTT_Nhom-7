"""Offline ASR scoring. Primary text normalization never changes words/numbers."""

import math
import random
import statistics
import unicodedata

NORMALIZER = "nfc-lower-punctuation-to-space-collapse-v1"


def normalize(text):
    """Keep accents, letters and digits; punctuation separates rather than joins."""
    text = unicodedata.normalize("NFC", text).lower()
    return " ".join(
        "".join(c if c.isalnum() or c.isspace() else " " for c in text).split()
    )


def distance(reference, hypothesis):
    previous = list(range(len(hypothesis) + 1))
    for i, left in enumerate(reference, 1):
        current = [i]
        for j, right in enumerate(hypothesis, 1):
            current.append(
                min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right))
            )
        previous = current
    return previous[-1]


def score(reference, hypothesis):
    reference, hypothesis = normalize(reference), normalize(hypothesis)
    if not reference:
        raise ValueError("A labelled acoustic sample must have reference words")
    return {
        "word_errors": distance(reference.split(), hypothesis.split()),
        "words": len(reference.split()),
        "character_errors": distance(reference, hypothesis),
        "characters": len(reference),
        "exact": reference == hypothesis,
    }


def percentile(values, fraction):
    return (
        sorted(values)[max(0, math.ceil(fraction * len(values)) - 1)]
        if values
        else None
    )


def summarize(rows):
    if not rows:
        raise ValueError("Cannot summarize an empty evaluation")
    words = sum(r["words"] for r in rows)
    chars = sum(r["characters"] for r in rows)
    timings = [r["wall_ms"] for r in rows if r.get("status") == 200]
    rss = [r["rss_mib"] for r in rows if isinstance(r.get("rss_mib"), (float, int))]
    return {
        "samples": len(rows),
        "speakers": len({r["speaker_id"] for r in rows}),
        "failed_samples": sum(r.get("status") != 200 for r in rows),
        "wer": sum(r["word_errors"] for r in rows) / words,
        "cer_including_spaces": sum(r["character_errors"] for r in rows) / chars,
        "utterance_exact_rate": sum(r["exact"] for r in rows) / len(rows),
        "wall_p50_ms": statistics.median(timings) if timings else None,
        "wall_p95_ms": percentile(timings, 0.95),
        "observed_rss_peak_mib": max(rss) if rss else None,
        "rss_scope": "worker RSS reported after each request; not sampled process peak",
        "words": words,
    }


def paired_delta(baseline, candidate, repeats=2000):
    """Paired speaker-cluster bootstrap; aggregate errors, never average clip WER."""
    if [(r["id"], r["sha256"]) for r in baseline] != [
        (r["id"], r["sha256"]) for r in candidate
    ]:
        raise ValueError("Paired reports must have identical ordered audio hashes")
    clusters = {}
    for before, after in zip(baseline, candidate, strict=True):
        clusters.setdefault(before["speaker_id"], []).append((before, after))
    speakers = sorted(clusters)
    rng = random.Random(20261023)
    deltas = []
    for _ in range(repeats):
        pairs = [p for s in rng.choices(speakers, k=len(speakers)) for p in clusters[s]]
        words = sum(before["words"] for before, _ in pairs)
        deltas.append(
            sum(after["word_errors"] - before["word_errors"] for before, after in pairs)
            / words
        )
    return {
        "candidate_minus_baseline_wer": summarize(candidate)["wer"]
        - summarize(baseline)["wer"],
        "exact_improved_samples": sum(
            not before["exact"] and after["exact"]
            for before, after in zip(baseline, candidate, strict=True)
        ),
        "exact_regressed_samples": sum(
            before["exact"] and not after["exact"]
            for before, after in zip(baseline, candidate, strict=True)
        ),
        "fewer_errors_samples": sum(
            after["word_errors"] < before["word_errors"]
            for before, after in zip(baseline, candidate, strict=True)
        ),
        "more_errors_samples": sum(
            after["word_errors"] > before["word_errors"]
            for before, after in zip(baseline, candidate, strict=True)
        ),
        "speaker_cluster_bootstrap_95_percent_interval": [
            percentile(deltas, 0.025),
            percentile(deltas, 0.975),
        ],
        "bootstrap_repeats": repeats,
        "seed": 20261023,
        "interpretation": "Negative favours candidate; read-speech corpus does not validate shopping or TC2",
    }
