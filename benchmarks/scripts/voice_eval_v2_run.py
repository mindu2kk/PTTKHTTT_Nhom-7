"""Run frozen V2 only after a recorded development-only configuration decision."""

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx

from voice_eval_corpus import PUBLIC, ROOT, sha, write_json
from voice_eval_metrics import NORMALIZER, score, summarize
from voice_eval_v2_corpus import MANIFEST, PRIVATE, verify

LOCK = PUBLIC / "evaluation-v2-configuration-lock.json"


def lock_configuration(args):
    verify()
    if LOCK.exists():
        raise RuntimeError("Configuration decision already locked; never overwrite")
    evidence = json.loads(args.development_evidence.read_text("utf8"))
    if evidence["split"] != "development":
        raise ValueError("Configuration must cite development evidence, not V2/heldout")
    record = {
        "locked_at": datetime.now(UTC).isoformat(),
        "v2_private_manifest_sha256": sha(MANIFEST.read_bytes()),
        "development_evidence": args.development_evidence.as_posix(),
        "development_evidence_sha256": sha(args.development_evidence.read_bytes()),
        "baseline": {"asr_profile": "whisper-base", "asr_without_timestamps": False},
        "candidate": {
            "asr_profile": "phowhisper-base",
            "asr_without_timestamps": args.candidate_without_timestamps == "true",
        },
        "decision_scope": "Configuration selected from publisher compatibility and development before V2 is decoded. V1 heldout already opened; V2 is new utterances, with overlapping speakers.",
    }
    write_json(LOCK, record)
    print(f"Configuration frozen: {LOCK}")


def run(args):
    verify()
    if not LOCK.exists():
        raise RuntimeError("Lock the development configuration before any V2 inference")
    decision = json.loads(LOCK.read_text("utf8"))
    if decision["v2_private_manifest_sha256"] != sha(MANIFEST.read_bytes()):
        raise RuntimeError("Manifest does not match locked decision")
    output = PUBLIC / f"evaluation-v2-{args.label}.json"
    if output.exists():
        raise RuntimeError("Refusing to overwrite V2 evidence")
    url = urlparse(args.endpoint)
    if url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Only local raw-audio worker endpoints are allowed")
    manifest = json.loads(MANIFEST.read_text("utf8"))
    active = PRIVATE.parent / "evaluation-active.lock"
    fd = os.open(active, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, f"{os.getpid()} v2-{args.label}".encode())
        rows, private_rows = [], []
        with httpx.Client(timeout=65, trust_env=False) as client:
            health_url = args.endpoint.rsplit("/", 1)[0] + "/health"
            health_before = client.get(health_url).json()
            if any(
                health_before.get(key) != expected
                for key, expected in decision[args.role].items()
            ):
                raise RuntimeError(
                    "Worker profile/decoder differs from frozen decision"
                )
            warmup = manifest["warmup"]
            start = time.perf_counter()
            response = client.post(
                args.endpoint,
                content=(ROOT / warmup["path"]).read_bytes(),
                headers={"Content-Type": "audio/wav"},
            )
            response.raise_for_status()
            data = response.json()
            initial = {
                "id": warmup["id"],
                "wall_ms": (time.perf_counter() - start) * 1000,
                "model_load_ms": data.get("model_load_ms"),
                "rss_mib": data.get("rss_mib"),
                "scope": "Repeated development warmup, not scored; process/OS cache coldness not forced",
            }
            for sample in manifest["samples"]:
                raw = (ROOT / sample["path"]).read_bytes()
                if sha(raw) != sample["sha256"]:
                    raise RuntimeError("Audio changed during V2")
                start = time.perf_counter()
                try:
                    response = client.post(
                        args.endpoint,
                        content=raw,
                        headers={"Content-Type": "audio/wav"},
                    )
                    status, data = response.status_code, response.json()
                except httpx.HTTPError as error:
                    status, data = 0, {"transport_error": type(error).__name__}
                elapsed = (time.perf_counter() - start) * 1000
                text = data.get("text", "") if status == 200 else ""
                row = {
                    k: v for k, v in sample.items() if k not in {"reference", "path"}
                }
                row.update(
                    {
                        **score(sample["reference"], text),
                        "status": status,
                        "wall_ms": elapsed,
                        "inference_ms": data.get("inference_ms"),
                        "rss_mib": data.get("rss_mib"),
                        "recognizer": data.get("recognizer"),
                        "model_revision": data.get("model_revision"),
                        "avg_logprob": data.get("avg_logprob"),
                    }
                )
                rows.append(row)
                private_rows.append(
                    {**row, "reference": sample["reference"], "hypothesis": text}
                )
                print(f"V2 {args.label} {sample['id']} HTTP{status}", flush=True)
            health_after = client.get(health_url).json()
        report = {
            "measured_at": datetime.now(UTC).isoformat(),
            "label": f"v2-{args.label}",
            "role": args.role,
            "split": "validation_v2",
            "endpoint": args.endpoint,
            "frozen_manifest_sha256": sha(MANIFEST.read_bytes()),
            "configuration_lock_sha256": sha(LOCK.read_bytes()),
            "configuration": decision[args.role],
            "primary_normalizer": NORMALIZER,
            "health_before": health_before,
            "health_after": health_after,
            "initial_request": initial,
            "summary": summarize(rows),
            "corpora": {
                corpus: summarize([r for r in rows if r["corpus"] == corpus])
                for corpus in sorted({r["corpus"] for r in rows})
            },
            "regional_smoke": {},
            "samples": rows,
            "limitations": manifest["limitations"]
            + " Post-response worker RSS is not sampled process peak. Timing is observational, not an SLA/speedup claim. Failed requests are empty hypotheses; no retries. No number-normalized intent metric.",
        }
        write_json(output, report)
        write_json(PRIVATE / output.name, {**report, "samples": private_rows})
        # Deliberately print status/path only. Review quality after both locked runs.
        print(f"V2 completed; evidence={output}", flush=True)
    finally:
        os.close(fd)
        active.unlink()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    lock = commands.add_parser("lock")
    lock.add_argument(
        "--candidate-without-timestamps", choices=["true", "false"], required=True
    )
    lock.add_argument("--development-evidence", type=Path, required=True)
    runner = commands.add_parser("run")
    runner.add_argument("--label", required=True)
    runner.add_argument("--role", choices=["baseline", "candidate"], required=True)
    runner.add_argument("--endpoint", default="http://127.0.0.1:19091/transcribe")
    args = parser.parse_args()
    if args.command == "lock":
        lock_configuration(args)
    else:
        if not args.label or not all(
            c.isascii() and (c.isalnum() or c in "-_") for c in args.label
        ):
            parser.error("label must contain only ASCII letters/digits/-/_")
        run(args)
