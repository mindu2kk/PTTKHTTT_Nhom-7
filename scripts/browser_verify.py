"""Run selected real-browser/model checks sequentially; retain per-script evidence."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = [
    "e2e_storefront",
    "e2e_text",
    "e2e_image",
    "e2e_voice",
    "e2e_ondevice",
    "e2e_recording",
    "e2e_commerce",
    "read_only_audit",
    "browser_lab",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("checks", nargs="*", choices=DEFAULT)
    args = parser.parse_args()
    reports = []
    for name in args.checks or DEFAULT:
        start = time.perf_counter()
        log = ROOT / "artifacts" / (name + "-final.log")
        with log.open("w", encoding="utf8") as output:
            result = subprocess.run(
                [sys.executable, str(ROOT / "benchmarks/scripts" / (name + ".py"))],
                cwd=ROOT,
                stdout=output,
                stderr=subprocess.STDOUT,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        reports.append(
            {
                "check": name,
                "exit_code": result.returncode,
                "seconds": round(time.perf_counter() - start, 3),
            }
        )
        print(json.dumps(reports[-1]), flush=True)
        if result.returncode:
            raise RuntimeError(f"{name} failed; see ignored artifact log.")
    (ROOT / "docs/evidence/browser-final-run.json").write_text(
        json.dumps(
            {
                "checks": reports,
                "scope": "Selected current Docker-stack regression; individual JSON evidence retains assertions and simulation labels",
            },
            indent=2,
        ),
        encoding="utf8",
    )


if __name__ == "__main__":
    main()
