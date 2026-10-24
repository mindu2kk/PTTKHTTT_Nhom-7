"""Single CPU inference process; lazy local models, one non-queued job, no network inference."""

import io
import os
import threading
import time
from pathlib import Path

import psutil
from fastapi import FastAPI, HTTPException, Request
from PIL import Image, UnidentifiedImageError

from asr_profiles import get_profile
from audio_decode import SAMPLE_RATE, decode_audio

MODEL_ROOT = Path(os.environ.get("MODEL_ROOT", "/models"))
CLIP_REVISION = "1a25a446712ba5ee05982a381eed697ef9b435cf"
ASR_PROFILE = get_profile(os.environ.get("ASR_MODEL_PROFILE", "whisper-base"))
Image.MAX_IMAGE_PIXELS = 12_000_000
app = FastAPI(title="HoodooMart local CPU inference", docs_url=None, redoc_url=None)
gate = threading.BoundedSemaphore(1)
clip = None
asr = None


@app.get("/health")
def health():
    return {
        "status": "ready",
        "clip_files": (MODEL_ROOT / "clip/open_clip_model.safetensors").is_file(),
        "asr_files": (ASR_PROFILE.path(MODEL_ROOT) / "model.bin").is_file(),
        "asr_profile": ASR_PROFILE.key,
        "asr_revision": ASR_PROFILE.revision,
        "asr_without_timestamps": ASR_PROFILE.without_timestamps,
        "clip_loaded": clip is not None,
        "asr_loaded": asr is not None,
        "rss_mib": round(psutil.Process().memory_info().rss / 1024**2, 2),
        "device": "cpu",
        "capacity": 1,
    }


def load_clip():
    global clip
    import torch
    import open_clip

    torch.set_num_threads(2)
    loaded = 0.0
    if clip is None:
        file = MODEL_ROOT / "clip/open_clip_model.safetensors"
        if not file.is_file():
            raise HTTPException(
                503, "Chưa có mô hình tìm ảnh cục bộ. Hãy dùng tìm từ khóa."
            )
        start = time.perf_counter()
        model, _, transform = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained=str(file), device="cpu"
        )
        model.eval()
        clip = (model, transform, open_clip.get_tokenizer("ViT-B-32"))
        loaded = (time.perf_counter() - start) * 1000
    return clip, loaded


def text_encode(text: str):
    if not gate.acquire(blocking=False):
        raise HTTPException(429, "Máy đang xử lý yêu cầu khác. Vui lòng thử lại.")
    start = time.perf_counter()
    try:
        import torch

        current, loaded = load_clip()
        tokens = current[2]([text])
        with torch.inference_mode():
            vector = current[0].encode_text(tokens)
            vector = vector / vector.norm(dim=-1, keepdim=True)
        return {
            "vector": vector[0].tolist(),
            "model_name": "OpenCLIP ViT-B/32",
            "model_revision": CLIP_REVISION,
            "dimension": 512,
            "device": "cpu",
            "model_load_ms": round(loaded, 3),
            "inference_ms": round((time.perf_counter() - start) * 1000, 3),
        }
    finally:
        gate.release()


@app.post("/encode-text")
async def encode_text(request: Request):
    import json
    from starlette.concurrency import run_in_threadpool

    raw = await bounded_body(request, 2048)
    try:
        body = json.loads(raw)
        if not isinstance(body, dict) or set(body) != {"text"}:
            raise ValueError
        text = body["text"]
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= 300:
            raise ValueError
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(422, "Mô tả sản phẩm không hợp lệ.") from None
    return await run_in_threadpool(text_encode, text)


def image_encode(raw: bytes):
    if not gate.acquire(blocking=False):
        raise HTTPException(
            429,
            "Máy đang xử lý yêu cầu khác. Vui lòng thử lại.",
            headers={"Retry-After": "1"},
        )
    started = time.perf_counter()
    try:
        try:
            image = Image.open(io.BytesIO(raw))
            if (
                image.format not in {"JPEG", "PNG", "WEBP"}
                or image.width * image.height > 12_000_000
                or min(image.size) < 16
            ):
                raise HTTPException(422, "Ảnh không hợp lệ.")
            image.load()
        except (
            UnidentifiedImageError,
            OSError,
            Image.DecompressionBombError,
            Image.DecompressionBombWarning,
        ) as error:
            raise HTTPException(422, "Ảnh bị hỏng hoặc quá lớn.") from error
        import torch

        current, loaded = load_clip()
        tensor = current[1](image.convert("RGB")).unsqueeze(0)
        with torch.inference_mode():
            vector = current[0].encode_image(tensor)
            vector = vector / vector.norm(dim=-1, keepdim=True)
        return {
            "vector": vector[0].tolist(),
            "model_name": "OpenCLIP ViT-B/32",
            "model_revision": CLIP_REVISION,
            "dimension": 512,
            "device": "cpu",
            "model_load_ms": round(loaded, 3),
            "inference_ms": round((time.perf_counter() - started) * 1000, 3),
            "rss_mib": round(psutil.Process().memory_info().rss / 1024**2, 2),
        }
    finally:
        gate.release()


@app.post("/encode")
async def encode(request: Request):
    raw = await bounded_body(request, 5 * 1024 * 1024)
    from starlette.concurrency import run_in_threadpool

    return await run_in_threadpool(image_encode, raw)


def speech_to_text(raw: bytes):
    global asr
    if not gate.acquire(blocking=False):
        raise HTTPException(429, "Máy đang xử lý yêu cầu khác. Vui lòng thử lại.")
    started = time.perf_counter()
    try:
        from faster_whisper import WhisperModel

        audio = decode_audio(raw)
        model_load_ms = 0.0
        if asr is None:
            local = ASR_PROFILE.path(MODEL_ROOT)
            if not (local / "model.bin").is_file():
                raise HTTPException(503, "Chưa có mô hình nhận giọng nói cục bộ.")
            t = time.perf_counter()
            try:
                ASR_PROFILE.validate_for_load(MODEL_ROOT)
            except ValueError as error:
                raise HTTPException(
                    503, "Mô hình nhận giọng cục bộ chưa vượt kiểm tra toàn vẹn."
                ) from error
            asr = WhisperModel(
                str(local),
                device="cpu",
                compute_type="int8",
                cpu_threads=2,
                num_workers=1,
                local_files_only=True,
            )
            model_load_ms = (time.perf_counter() - t) * 1000
        segments, info = asr.transcribe(
            audio,
            language="vi",
            beam_size=3,
            best_of=3,
            temperature=0,
            condition_on_previous_text=False,
            vad_filter=False,
            without_timestamps=ASR_PROFILE.without_timestamps,
            max_new_tokens=160,
            repetition_penalty=1.1,
            no_repeat_ngram_size=3,
        )
        segments = list(segments)
        transcript = " ".join(s.text.strip() for s in segments).strip()
        if not transcript:
            raise HTTPException(
                422, "Chưa nhận được câu nói. Hãy ghi lại hoặc nhập văn bản."
            )
        probability = sum(s.avg_logprob for s in segments) / len(segments)
        warnings = ["Kiểm tra và sửa bản ghi trước khi tìm sản phẩm."]
        if probability < -0.5:
            warnings.append(
                "Bản ghi có đoạn chưa chắc chắn. Hãy kiểm tra kỹ tên sản phẩm và mức giá."
            )
        return {
            "text": transcript,
            "language": "vi",
            "duration_seconds": round(len(audio) / SAMPLE_RATE, 3),
            "recognizer": ASR_PROFILE.recognizer,
            "model_revision": ASR_PROFILE.revision,
            "without_timestamps": ASR_PROFILE.without_timestamps,
            "inference_ms": round((time.perf_counter() - started) * 1000, 3),
            "model_load_ms": round(model_load_ms, 3),
            "avg_logprob": round(probability, 4),
            "warnings": warnings,
            "rss_mib": round(psutil.Process().memory_info().rss / 1024**2, 2),
        }
    finally:
        gate.release()


@app.post("/transcribe")
async def transcribe(request: Request):
    raw = await bounded_body(request, 2 * 1024 * 1024)
    from starlette.concurrency import run_in_threadpool

    return await run_in_threadpool(speech_to_text, raw)


async def bounded_body(request: Request, limit: int) -> bytes:
    chunks = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > limit:
            raise HTTPException(413, "Tệp vượt quá dung lượng cho phép.")
        chunks.append(chunk)
    return b"".join(chunks)
