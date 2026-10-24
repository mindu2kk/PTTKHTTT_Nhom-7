"""Supplemental region smoke on the9 historical ViMD development clips.

Original frozen manifest omitted the old source region labels. Join the existing
rights-reviewed selection by ID, report its SHA, never alter the frozen manifest.
"""

import argparse
import json
from pathlib import Path

from voice_eval_corpus import ROOT, sha, write_json
from voice_eval_metrics import paired_delta, summarize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise RuntimeError("Refusing to overwrite region evidence")
    region_path = ROOT / "data/private/vimd/regional-selection.json"
    metadata = json.loads(region_path.read_text("utf8"))
    regions = {f"vimd:{r['id']}": r["region"] for r in metadata["samples"]}
    baseline = json.loads(args.baseline.read_text("utf8"))
    if baseline["split"] != "development":
        raise ValueError("Historical regions only apply to development")
    rows = [r for r in baseline["samples"] if r["id"] in regions]
    result = {
        "split": "development",
        "baseline": baseline["label"],
        "frozen_manifest_sha256": baseline["frozen_manifest_sha256"],
        "auxiliary_existing_region_metadata_sha256": sha(region_path.read_bytes()),
        "regions": {
            region: {
                "baseline": summarize([r for r in rows if regions[r["id"]] == region])
            }
            for region in sorted(set(regions.values()))
        },
        "limitations": "Three historical clips per source region; development smoke, not an independent regional quality gate. Joins labels only; primary frozen manifest remains unchanged.",
    }
    if args.candidate:
        candidate = json.loads(args.candidate.read_text("utf8"))
        if (
            candidate["frozen_manifest_sha256"] != baseline["frozen_manifest_sha256"]
            or candidate["split"] != "development"
        ):
            raise ValueError("Mismatched candidate protocol")
        candidate_rows = [r for r in candidate["samples"] if r["id"] in regions]
        result["candidate"] = candidate["label"]
        for region, details in result["regions"].items():
            after = [r for r in candidate_rows if regions[r["id"]] == region]
            before = [r for r in rows if regions[r["id"]] == region]
            details.update(
                candidate=summarize(after), paired=paired_delta(before, after)
            )
    write_json(args.output, result)
    print(json.dumps(result["regions"]))


if __name__ == "__main__":
    main()
