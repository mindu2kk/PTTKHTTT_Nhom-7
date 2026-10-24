"""Run inside existing inference container with only copied evaluation WAVs; no downloads."""

import json
import sys
import time
from pathlib import Path

import main as worker
from search_voice_policies import decoding_options

root = Path(sys.argv[1])
policy = sys.argv[2]
samples = json.loads((root / "samples.json").read_text("utf8"))
worker.speech_to_text((root / samples[0]["file"]).read_bytes())
model = worker.asr


class ContextModel:
    def transcribe(self, audio, **kwargs):
        return model.transcribe(audio, **decoding_options(policy))


worker.asr = ContextModel()
results = []
for sample in samples:
    started = time.perf_counter()
    result = worker.speech_to_text((root / sample["file"]).read_bytes())
    results.append(
        {
            "id": sample["id"],
            "text": result["text"],
            "inference_ms": (time.perf_counter() - started) * 1000,
        }
    )
    print(sample["id"], flush=True)
(root / f"{policy}.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), "utf8"
)
