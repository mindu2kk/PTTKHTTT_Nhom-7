"""Measured noise and mixed-term stress cases; failures remain visible, no fake ASR."""

import array
import io
import json
import math
import random
import subprocess
import time
import wave
from pathlib import Path

import httpx

from voice_integration import distance, normalized

ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "data/private/voice-stress"


def main():
    STORE.mkdir(parents=True, exist_ok=True)
    source = ROOT / "data/private/vivos"
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf8"))
    cases = []
    rng = random.Random(42)
    for sample in manifest["samples"][:3]:
        with wave.open(str(source / sample["file"]), "rb") as audio:
            params = audio.getparams()
            assert params.sampwidth == 2
            pcm = array.array("h", audio.readframes(audio.getnframes()))
        rms = math.sqrt(sum(v * v for v in pcm) / len(pcm))
        sigma = rms / math.sqrt(10)
        noisy = array.array(
            "h", (max(-32768, min(32767, round(v + rng.gauss(0, sigma)))) for v in pcm)
        )
        output = io.BytesIO()
        with wave.open(output, "wb") as audio:
            audio.setparams(params)
            audio.writeframes(noisy.tobytes())
        file = STORE / ("noise-" + sample["id"] + ".wav")
        file.write_bytes(output.getvalue())
        cases.append(
            {
                "id": file.stem,
                "kind": "VIVOS human waveform + generated Gaussian noise, nominal SNR10dB, seed42",
                "path": file,
                "reference": sample["reference"],
            }
        )
    for index, phrase in enumerate(
        [
            "tôi muốn mua áo hoodie size XL dưới năm trăm k",
            "áo len nam size L dưới năm trăm nghìn",
        ]
    ):
        name = f"stress-mixed-{index}.wav"
        file = STORE / name
        subprocess.run(
            [
                "docker",
                "exec",
                "hoodoomart-inference-1",
                "espeak-ng",
                "-v",
                "vi",
                "-s",
                "150",
                "-w",
                "/tmp/" + name,
                phrase,
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["docker", "cp", "hoodoomart-inference-1:/tmp/" + name, str(file)],
            check=True,
            capture_output=True,
        )
        cases.append(
            {
                "id": file.stem,
                "kind": "Synthetic eSpeak mixed English/product sizes/Vietnamese spoken price; not a human speaker",
                "path": file,
                "reference": phrase,
            }
        )
    results = []
    with httpx.Client(
        base_url="http://localhost:8000", timeout=65, trust_env=False
    ) as client:
        for case in cases:
            start = time.perf_counter()
            response = client.post(
                "/api/v1/search/voice",
                files={
                    "audio": (case["path"].name, case["path"].read_bytes(), "audio/wav")
                },
            )
            data = response.json()
            hyp = data["text"] if response.status_code == 200 else ""
            ref_n, hyp_n = normalized(case["reference"]), normalized(hyp)
            result = {k: v for k, v in case.items() if k != "path"}
            result.update(
                hypothesis=hyp,
                status=response.status_code,
                wer=distance(ref_n.split(), hyp_n.split()) / len(ref_n.split()),
                cer=distance(ref_n, hyp_n) / len(ref_n),
                http_ms=round((time.perf_counter() - start) * 1000, 3),
            )
            if hyp and len(hyp) <= 300:
                search = client.post(
                    "/api/v1/search/text", json={"q": hyp, "modality": "voice"}
                )
                if search.status_code == 200:
                    result["actual_query"] = search.json()["query"]
            results.append(result)
            print(
                json.dumps(
                    {"id": case["id"], "status": result["status"], "wer": result["wer"]}
                ),
                flush=True,
            )
    report = {
        "scope": "Three human VIVOS clips with controlled noise + two synthetic mixed-language shopping utterances; no regional or population accuracy claim",
        "vivos_source": "https://zenodo.org/records/7068130",
        "authors": ["Hieu-Thi Luong", "Hai-Quan Vu"],
        "license": "VIVOS-derived excerpts/audio: CC-BY-NC-SA-4.0, academic only; audio stays private",
        "results": results,
        "limitations": "Tiny stress smoke sample, generated noise is not real ambient recording; synthetic size/English tests expose failures, not language capability proof",
    }
    (ROOT / "docs/evidence/voice-stress.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
    )


if __name__ == "__main__":
    main()
