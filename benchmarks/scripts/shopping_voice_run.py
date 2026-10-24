"""Run frozen shopping cases against the real API; explicit modality/source labels."""

import argparse
import hashlib
import json
import mimetypes
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from shopping_voice_oracle import FIXTURE, ROOT, norm
from shopping_voice_score import score_case, summarize

ORACLE_SHA256 = "5b62b3300def0d67d88933cd6505e7fb758147605c43db0a0767c50c798d8986"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_live_catalog(client, fixture):
    products, page, total = [], 1, None
    while total is None or len(products) < total:
        response = client.get(
            "/api/v1/products", params={"page": page, "page_size": 24}
        )
        response.raise_for_status()
        data = response.json()
        total = data["total"]
        if not data["items"]:
            raise ValueError("Public catalog pagination ended before declared total")
        products.extend(data["items"])
        page += 1
    by_id = {row["id"]: row for row in products}
    for expected in fixture["catalog_snapshot"]:
        actual = by_id.get(expected["id"])
        if actual is None:
            raise ValueError(f"Frozen product no longer public: {expected['id']}")
        for key in ["category_id", "price_vnd", "color", "gender", "brand", "name_vi"]:
            if norm(actual.get(key)) != norm(expected.get(key)):
                raise ValueError(
                    f"Catalog changed; do not rewrite oracle: {expected['id']} {key}"
                )
        if (
            actual.get("rights_status") != "approved"
            or actual.get("verification_status") != "verified"
            or actual.get("data_profile") != "real_demo"
        ):
            raise ValueError("Public product lost reviewed provenance")
    return {
        "live_public_count": len(products),
        "frozen_products_verified": len(fixture["catalog_snapshot"]),
        "canonical_snapshot_sha256": sha(
            json.dumps(products, sort_keys=True, ensure_ascii=False).encode()
        ),
        "status": "verified_against_live_public_API",
    }


def load_inputs(args, fixture):
    if args.input_kind == "clean_text":
        return {case["id"]: {"text": case["query"]} for case in fixture["cases"]}
    if args.manifest is None:
        return {}
    manifest = json.loads(args.manifest.read_text("utf8"))
    if manifest.get("oracle_sha256") != ORACLE_SHA256:
        raise ValueError("Input manifest must reference exact frozen oracle SHA256")
    rows = manifest.get("records", [])
    result = {}
    for row in rows:
        if row["case_id"] in result:
            raise ValueError(
                "Select one predeclared recording per case, not best-of retries"
            )
        result[row["case_id"]] = row
    return result


def audio_bytes(record, args):
    expected_kind = "human" if args.input_kind == "human_audio" else "synthetic"
    if record.get("audio_kind") != expected_kind:
        raise ValueError("audio_kind does not match suite; never relabel TTS as human")
    path = (ROOT / record["path"]).resolve()
    private = (ROOT / "data/private/shopping-voice").resolve()
    if not path.is_relative_to(private):
        raise ValueError("Domain audio must remain in private shopping-voice folder")
    raw = path.read_bytes()
    if not raw or len(raw) > 2 * 1024 * 1024 or sha(raw) != record.get("sha256"):
        raise ValueError("Missing/changed/oversized audio")
    if expected_kind == "human" and (
        record.get("consent") is not True
        or record.get("rights_status") not in {"user_consent", "approved_evaluation"}
        or not record.get("speaker_id")
    ):
        raise ValueError(
            "Human domain audio requires consent, rights and pseudonymous speaker ID"
        )
    return raw, mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-kind",
        choices=[
            "clean_text",
            "artificial_degraded_text",
            "synthetic_audio",
            "human_audio",
        ],
        default="clean_text",
    )
    parser.add_argument(
        "--mode", choices=["first_pass", "reviewed"], default="first_pass"
    )
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--api", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("Refusing to overwrite measured evidence")
    if urlparse(args.api).hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Only local API allowed")
    if sha(FIXTURE.read_bytes()) != ORACLE_SHA256:
        raise ValueError("Frozen oracle changed")
    fixture = json.loads(FIXTURE.read_text("utf8"))
    inputs = load_inputs(args, fixture)
    rows = []
    with httpx.Client(
        base_url=args.api,
        timeout=65,
        trust_env=False,
        headers={"Origin": "http://localhost:3000"},
    ) as client:
        grounding = verify_live_catalog(client, fixture)
        for case in fixture["cases"]:
            record = inputs.get(case["id"])
            if record is None:
                continue
            eligible = False
            try:
                if args.input_kind in {"human_audio", "synthetic_audio"}:
                    raw, mime = audio_bytes(record, args)
                    response = client.post(
                        "/api/v1/search/voice",
                        files={
                            "audio": (
                                "capture" + Path(record["path"]).suffix,
                                raw,
                                mime,
                            )
                        },
                    )
                    if response.status_code != 200:
                        row = score_case(case, {}, response.status_code)
                        row["failure_reason"] = "asr_http_error"
                        rows.append(row)
                        continue
                    query = response.json().get("text", "")
                    eligible = (
                        args.input_kind == "human_audio" and args.mode == "first_pass"
                    )
                    if args.mode == "reviewed":
                        if record.get("user_confirmed") is not True or not record.get(
                            "reviewed_text"
                        ):
                            raise ValueError(
                                "Reviewed mode requires explicit user-confirmed text"
                            )
                        query = record["reviewed_text"]
                else:
                    query = record["text"]
                response = client.post(
                    "/api/v1/search/text",
                    json={
                        "q": query,
                        "modality": "text"
                        if args.input_kind == "clean_text"
                        else "voice",
                        "page_size": 12,
                        **case["ui_filters"],
                    },
                )
                row = score_case(case, response.json(), response.status_code)
                row.update(human_audio_eligible=eligible)
            except httpx.HTTPError as error:
                row = score_case(case, {}, 0)
                row["failure_reason"] = type(error).__name__
            except (ValueError, KeyError, OSError) as error:
                row = score_case(case, {}, 0)
                row["failure_reason"] = type(error).__name__
            rows.append(row)
            print(
                f"{case['id']} HTTP{row['http_status']} success={row['success']}",
                flush=True,
            )
    report = {
        "measured_at": datetime.now(UTC).isoformat(),
        "oracle_sha256": ORACLE_SHA256,
        "suite_scope": "development_calibration_text; reserved domain human recordings must be collected untuned separately",
        "live_catalog_grounding": grounding,
        "summary": summarize(fixture["cases"], rows, args.input_kind, args.mode),
        "rows": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(json.dumps(report["summary"], ensure_ascii=True))


if __name__ == "__main__":
    main()
