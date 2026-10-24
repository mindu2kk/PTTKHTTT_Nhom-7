"""Independent semantic/product scoring. Text/TTS cannot pass human voice gate."""

from collections import Counter

from shopping_voice_oracle import matches, norm


def slot_tuple(slot):
    value = slot.get("value")
    if slot.get("key", "").startswith("price_"):
        value = value if type(value) is int else ("invalid_vnd", str(value))
    else:
        value = norm(value)
    return slot.get("key"), value, slot.get("operator", "eq")


def score_case(case, body, status=200):
    expected = {slot_tuple(slot) for slot in case["slots"]}
    observed = {
        slot_tuple(slot) for slot in body.get("query", {}).get("hard_filters", [])
    }
    missing_slots = expected - observed
    extra_slots = observed - expected
    intent = status == 200 and body.get("search_type") == case["expected_intent"]
    preserved = intent and not missing_slots and not extra_slots
    violations = []
    ids = []
    for item in body.get("items", []):
        product = item.get("product", {})
        identifier = product.get("id")
        ids.append(identifier)
        public = (
            product.get("data_profile") == "real_demo"
            and product.get("verification_status") == "verified"
            and product.get("rights_status") == "approved"
            and product.get("source_id") == "amazon-berkeley-objects"
            and bool(product.get("image_url"))
        )
        money_integer = type(product.get("price_vnd")) is int
        constraints_ok = False
        bad_slots = []
        try:
            constraints_ok = money_integer and matches(product, case["slots"])
            bad_slots = [slot["key"] for slot in case["slots"] if not matches(product, [slot])]
        except (KeyError, TypeError, ValueError):
            bad_slots = ["invalid_product_fields"]
        if not public or not constraints_ok:
            violations.append(
                {
                    "id": identifier,
                    "public_provenance_ok": public,
                    "integer_vnd": money_integer,
                    "all_requested_constraints_ok": constraints_ok,
                    "violated_slot_keys": bad_slots,
                }
            )
    hit = bool(set(ids[:5]) & set(case["acceptable_product_ids"]))
    return {
        "case_id": case["id"],
        "http_status": status,
        "intent_preserved": intent,
        "all_semantic_slots_preserved": preserved,
        "missing_slots": [list(s) for s in sorted(missing_slots, key=str)],
        "unexpected_slots": [list(s) for s in sorted(extra_slots, key=str)],
        "top5_product_hit": hit,
        "returned_ids": ids,
        "hard_constraint_violations": violations,
        "success": preserved and hit and not violations,
    }


def summarize(cases, rows, input_kind, mode="first_pass"):
    if len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError("One scored result per case; no best-of retry selection")
    expected_ids = {case["id"] for case in cases}
    if any(row["case_id"] not in expected_ids for row in rows):
        raise ValueError("Unknown case ID")
    count, covered = len(cases), len(rows)
    success = sum(bool(row.get("success")) for row in rows)
    violations = sum(len(row.get("hard_constraint_violations", [])) for row in rows)
    violation_keys = Counter(key for row in rows for violation in row.get("hard_constraint_violations", []) for key in violation.get("violated_slot_keys", ["unspecified_legacy_evidence"]))
    real = input_kind == "human_audio" and mode == "first_pass"
    eligible = sum(bool(row.get("human_audio_eligible")) for row in rows)
    human_ready = real and covered == count and eligible == count
    if not real:
        voice_status = "not_applicable_text_synthetic_or_reviewed"
    elif not human_ready:
        voice_status = "pending_missing_or_unverified_human_audio"
    else:
        voice_status = (
            "passed" if success / count >= 0.7 and violations == 0 else "failed"
        )
    return {
        "fixed_denominator": count,
        "covered_cases": covered,
        "missing_cases": count - covered,
        "successes": success,
        "semantic_and_product_success_rate": success / count if covered else None,
        "all_slots_preserved_cases": sum(
            bool(row.get("all_semantic_slots_preserved")) for row in rows
        ),
        "top5_hit_cases": sum(bool(row.get("top5_product_hit")) for row in rows),
        "hard_constraint_violations": violations,
        "hard_violation_slot_breakdown": dict(violation_keys),
        "http_or_transport_errors": sum(row.get("http_status") != 200 for row in rows),
        "failure_reasons": dict(
            Counter(
                row.get("failure_reason") for row in rows if row.get("failure_reason")
            )
        ),
        "human_audio_eligible_cases": eligible,
        "input_kind": input_kind,
        "mode": mode,
        "text_suite_status": "not_applicable_audio_suite" if input_kind in {"human_audio", "synthetic_audio"} else "not_run"
        if not covered
        else (
            "target_met_on_development"
            if success / count >= 0.7 and violations == 0
            else "below_target_or_safety_failure"
        ),
        "real_first_pass_voice_gate": voice_status,
        "gate_note": "Success = every requested semantic slot preserved + at least1 acceptable public product inTop5 + zero requested hard/provenance violations across all returned items. All100cases remain denominator; missing/timeouts/errors fail. Text/artificial/TTS/reviewed results never prove70% first-pass human voice.",
    }
