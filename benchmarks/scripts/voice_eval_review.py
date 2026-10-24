"""Collect measured quality gates after the fixed V2 experiment; never deploy."""

import json
from datetime import UTC, datetime

from voice_eval_corpus import PUBLIC, sha, write_json


def main():
    names = [
        "evaluation-v2-base-fixed.json",
        "evaluation-v2-pho-text-int8.json",
        "evaluation-v2-paired.json",
        "evaluation-base-fresh-fixed-heldout.json",
        "evaluation-pho-text-int8-heldout.json",
        "evaluation-repeated-v1-paired.json",
        "evaluation-base-int8-development.json",
        "evaluation-pho-text-int8-development.json",
        "evaluation-v2-configuration-lock.json",
        "evaluation-v2-decoder-lock.json",
    ]
    sources = {name: json.loads((PUBLIC / name).read_text("utf8")) for name in names}
    base = sources["evaluation-v2-base-fixed.json"]
    candidate = sources["evaluation-v2-pho-text-int8.json"]
    before = sources["evaluation-base-fresh-fixed-heldout.json"]
    after = sources["evaluation-pho-text-int8-heldout.json"]
    if (
        base["configuration_lock_sha256"] != candidate["configuration_lock_sha256"]
        or base["frozen_manifest_sha256"] != candidate["frozen_manifest_sha256"]
    ):
        raise RuntimeError("V2 configuration/manifest differs between paired runs")
    regressions = [
        {
            "id": left["id"],
            "baseline_errors": left["word_errors"],
            "candidate_errors": right["word_errors"],
            "reference_words": left["words"],
        }
        for left, right in zip(before["samples"], after["samples"], strict=True)
        if right["word_errors"] > left["word_errors"]
    ]
    result = {
        "reviewed_at": datetime.now(UTC).isoformat(),
        "source_sha256": {name: sha((PUBLIC / name).read_bytes()) for name in names},
        "selected_configuration": sources["evaluation-v2-configuration-lock.json"][
            "candidate"
        ],
        "shared_decoder_lock": sources["evaluation-v2-decoder-lock.json"],
        "primary_v2": {
            "scope": "New utterances,29VIVOS/19source speaker IDs, overlapping prior speakers; no new ViMD eligible",
            "baseline": base["summary"],
            "candidate": candidate["summary"],
            "paired": sources["evaluation-v2-paired.json"]["paired"],
            "relative_wer_reduction": 1
            - candidate["summary"]["wer"] / base["summary"]["wer"],
            "both_initial_requests": {
                "baseline": base["initial_request"],
                "candidate": candidate["initial_request"],
            },
            "asr_only_observed_rss_delta_mib": candidate["summary"][
                "observed_rss_peak_mib"
            ]
            - base["summary"]["observed_rss_peak_mib"],
        },
        "secondary_v1_repeated": {
            "scope": "Reused original heldout after compatibility flag was selected; repeated validation, not a new blind test",
            "baseline": before["summary"],
            "candidate": after["summary"],
            "paired": sources["evaluation-repeated-v1-paired.json"]["paired"],
            "corpora": {
                corpus: {
                    "baseline": before["corpora"][corpus],
                    "candidate": after["corpora"][corpus],
                }
                for corpus in before["corpora"]
            },
            "regressed_samples": regressions,
        },
        "development_not_acceptance": {
            "baseline": sources["evaluation-base-int8-development.json"]["corpora"],
            "candidate": sources["evaluation-pho-text-int8-development.json"][
                "corpora"
            ],
        },
        "observations": {
            "primary_v2_wer_and_cer_lower": candidate["summary"]["wer"]
            < base["summary"]["wer"]
            and candidate["summary"]["cer_including_spaces"]
            < base["summary"]["cer_including_spaces"],
            "primary_v2_no_http_errors": base["summary"]["failed_samples"]
            == candidate["summary"]["failed_samples"]
            == 0,
            "secondary_each_corpus_wer_and_cer_lower": all(
                after["corpora"][corpus]["wer"] < before["corpora"][corpus]["wer"]
                and after["corpora"][corpus]["cer_including_spaces"]
                < before["corpora"][corpus]["cer_including_spaces"]
                for corpus in before["corpora"]
            ),
        },
        "limitations": [
            "No shopping oracle, TC2, physical microphone/noise/mixed-English population validation; do not call all voice errors resolved.",
            "V2 is utterance-disjoint, not speaker-independent; V1 repeated is already observed.",
            "Post-response RSS is not process peak. V2 median wall time is higher for candidate; no universal speedup/SLA claim.",
            "Configuration was fixed before V2; no new tuning on V2. Profile deployment remains coordinator decision.",
        ],
    }
    output = PUBLIC / "evaluation-final-review.json"
    if output.exists():
        raise RuntimeError("Refusing to overwrite final evidence")
    write_json(output, result)
    print(json.dumps(result["observations"]))


if __name__ == "__main__":
    main()
