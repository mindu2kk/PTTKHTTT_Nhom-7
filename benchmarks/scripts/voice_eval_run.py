"""Sequential local-worker ASR benchmark, after the coordinator grants a CPU slot.

No model/dataset downloads. Gate429/error is recorded, never hidden by retries.
Public evidence omits source transcripts; private diagnostics retain them.
"""

import argparse
import json
import os
import time
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx

from voice_eval_corpus import PRIVATE, PUBLIC, ROOT, sha, verify, write_json
from voice_eval_metrics import NORMALIZER, paired_delta, score, summarize


def run(args):
    verify()
    url = urlparse(args.endpoint)
    if url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Only explicitly local HTTP worker endpoints are allowed")
    output = PUBLIC / f"evaluation-{args.label}-{args.split}.json"
    if output.exists():
        raise RuntimeError(f"Evidence exists; use a new label: {output}")
    manifest_path = PRIVATE / "evaluation-manifest.json"
    manifest = json.loads(manifest_path.read_text("utf8"))
    samples = [r for r in manifest["samples"] if r["split"] == args.split]
    lock = PRIVATE / "evaluation-active.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, f"{os.getpid()} {args.label}".encode())
        results = []
        private_rows = []
        with httpx.Client(timeout=args.timeout, trust_env=False) as client:
            warmup = next(r for r in manifest["samples"] if r["split"] == "development")
            started = time.perf_counter()
            response = client.post(
                args.endpoint,
                content=(ROOT / warmup["path"]).read_bytes(),
                headers={"Content-Type": "audio/wav"},
            )
            response.raise_for_status()
            warm_data = response.json()
            cold = {
                "sample": warmup["id"],
                "status": response.status_code,
                "wall_ms": (time.perf_counter() - started) * 1000,
                "model_load_ms": warm_data.get("model_load_ms"),
                "rss_mib": warm_data.get("rss_mib"),
                "label": "initial request; process/OS-cache coldness not forced",
            }
            for sample in samples:
                raw = (ROOT / sample["path"]).read_bytes()
                if sha(raw) != sample["sha256"]:
                    raise RuntimeError("Audio modified during benchmark")
                started = time.perf_counter()
                try:
                    response = client.post(
                        args.endpoint,
                        content=raw,
                        headers={"Content-Type": "audio/wav"},
                    )
                    status = response.status_code
                    data = response.json()
                except httpx.HTTPError as error:
                    status, data = 0, {"transport_error": type(error).__name__}
                elapsed = (time.perf_counter() - started) * 1000
                text = data.get("text", "") if status == 200 else ""
                row = {
                    k: v for k, v in sample.items() if k not in {"reference", "path"}
                }
                row.update(
                    {
                        **score(sample["reference"], text),
                        "status": status,
                        "wall_ms": round(elapsed, 3),
                        "inference_ms": data.get("inference_ms"),
                        "rss_mib": data.get("rss_mib"),
                        "recognizer": data.get("recognizer"),
                        "model_revision": data.get("model_revision"),
                    }
                )
                results.append(row)
                private_rows.append(
                    {**row, "reference": sample["reference"], "hypothesis": text}
                )
                print(
                    f"{args.label} {args.split} {sample['id']} HTTP{status}", flush=True
                )
        report = {
            "measured_at": datetime.now(UTC).isoformat(),
            "label": args.label,
            "split": args.split,
            "endpoint": args.endpoint,
            "frozen_manifest_sha256": sha(manifest_path.read_bytes()),
            "primary_normalizer": NORMALIZER,
            "normalization_policy": "NFC/lowercase; punctuation becomes space; collapse whitespace; accents and numeric digits unchanged. No product/context autocorrection. CER includes normalized spaces.",
            "initial_request": cold,
            "summary": summarize(results),
            "corpora": {
                corpus: summarize([r for r in results if r["corpus"] == corpus])
                for corpus in sorted({r["corpus"] for r in results})
            },
            "regional_smoke": {
                region: summarize([r for r in results if r.get("region") == region])
                for region in sorted({r["region"] for r in results if r.get("region")})
            },
            "worst_samples_by_wer": [
                {
                    "id": r["id"],
                    "wer": r["word_errors"] / r["words"],
                    "status": r["status"],
                }
                for r in sorted(
                    results, key=lambda r: r["word_errors"] / r["words"], reverse=True
                )[:5]
            ],
            "samples": results,
            "limitations": "No shopping/TC2 or physical microphone quality claim. No numeric-normalized intent metric: no labelled shopping corpus available. Initial warmup separate; requests serialized, no concurrency benchmark. Observed post-response RSS is not true process peak. Any failed sample scored as empty hypothesis.",
        }
        write_json(output, report)
        write_json(PRIVATE / output.name, {**report, "samples": private_rows})
        print(json.dumps(report["summary"], ensure_ascii=True))
    finally:
        os.close(fd)
        lock.unlink()


def compare(args):
    baseline = json.loads(args.baseline.read_text("utf8"))
    candidate = json.loads(args.candidate.read_text("utf8"))
    for key in ["split", "frozen_manifest_sha256", "primary_normalizer"]:
        if baseline[key] != candidate[key]:
            raise ValueError(f"Paired protocol differs: {key}")
    result = {
        "baseline": baseline["label"],
        "candidate": candidate["label"],
        "split": baseline["split"],
        "frozen_manifest_sha256": baseline["frozen_manifest_sha256"],
        "primary_normalizer": baseline["primary_normalizer"],
        "baseline_summary": baseline["summary"],
        "candidate_summary": candidate["summary"],
        "paired": paired_delta(baseline["samples"], candidate["samples"]),
        "corpora": {
            corpus: paired_delta(
                [r for r in baseline["samples"] if r["corpus"] == corpus],
                [r for r in candidate["samples"] if r["corpus"] == corpus],
            )
            for corpus in baseline["corpora"]
        },
        "regional_smoke": {
            region: paired_delta(
                [r for r in baseline["samples"] if r.get("region") == region],
                [r for r in candidate["samples"] if r.get("region") == region],
            )
            for region in baseline.get("regional_smoke", {})
        },
        "limitations": baseline["limitations"],
    }
    if args.output.exists():
        raise RuntimeError("Refusing to overwrite paired evidence")
    write_json(args.output, result)
    print(json.dumps(result["paired"]))


if __name__ == "__main__":
    from pathlib import Path

    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    runner = commands.add_parser("run")
    runner.add_argument(
        "--label", required=True, help="Immutable run identifier (no spaces or slashes)"
    )
    runner.add_argument("--split", choices=["development", "heldout"], required=True)
    runner.add_argument("--endpoint", default="http://127.0.0.1:19090/transcribe")
    runner.add_argument("--timeout", type=float, default=65)
    paired = commands.add_parser("compare")
    paired.add_argument("baseline", type=Path)
    paired.add_argument("candidate", type=Path)
    paired.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "run":
        if not args.label or not all(
            c.isascii() and (c.isalnum() or c in "-_") for c in args.label
        ):
            parser.error("label must contain only ASCII letters, digits, '-' or '_'")
        run(args)
    else:
        compare(args)
