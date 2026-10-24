import hashlib
import io
import math
import time
import warnings
from collections import OrderedDict
from dataclasses import replace
from pathlib import PurePath

import httpx
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.domain.media import CleanImage, EncodedImage, MediaError, Transcript

Image.MAX_IMAGE_PIXELS = 12_000_000
CLIP_REVISION = "1a25a446712ba5ee05982a381eed697ef9b435cf"
WHISPER_REVISION = "ebe41f70d5b6dfa9166e2c581c45c9c0cfc57b66"
SPEECH_MODELS = {
    WHISPER_REVISION: "faster-whisper base int8 CPU",
    "7ebdb9e88f5cc5271fb88f4d642c82ff9388650e": "PhoWhisper base int8 CPU",
}


def sanitize(content: bytes, mime: str, filename: str) -> CleanImage:
    if len(content) > 5 * 1024 * 1024:
        raise MediaError(413, "Ảnh tối đa 5 MB. Hãy chọn ảnh nhỏ hơn.")
    suffix = PurePath(filename.lower()).suffix
    expected = {
        "image/jpeg": ({".jpg", ".jpeg"}, "JPEG"),
        "image/png": ({".png"}, "PNG"),
        "image/webp": ({".webp"}, "WEBP"),
    }
    if mime not in expected or suffix not in expected[mime][0]:
        raise MediaError(422, "Chỉ nhận ảnh JPEG, PNG hoặc WebP; chưa hỗ trợ HEIC.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image: Image.Image = Image.open(io.BytesIO(content))
            if (
                image.format != expected[mime][1]
                or image.width * image.height > 12_000_000
                or min(image.size) < 16
            ):
                raise MediaError(
                    422, "Nội dung ảnh không khớp định dạng hoặc kích thước không phù hợp."
                )
            image.verify()
            image = Image.open(io.BytesIO(content))
            width, height = image.size
            image = image.convert("RGB")
            image.info.clear()
            image.thumbnail((1600, 1600))
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            raw = buffer.getvalue()
            if len(raw) > 5 * 1024 * 1024:
                image.thumbnail((1280, 1280))
                buffer = io.BytesIO()
                image.save(buffer, format="PNG")
                raw = buffer.getvalue()
            return CleanImage(raw, hashlib.sha256(raw).hexdigest(), width, height)
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise MediaError(
            422, "Ảnh bị hỏng hoặc có kích thước quá lớn. Vui lòng chọn ảnh khác."
        ) from error


class PillowMediaValidator:
    async def clean_image(self, content: bytes, mime: str, filename: str) -> CleanImage:
        return await run_in_threadpool(sanitize, content, mime, filename)


class HttpImageEncoder:
    def __init__(self, url: str):
        self.url = url
        self.cache: OrderedDict[str, tuple[float, EncodedImage]] = OrderedDict()

    async def encode(self, image: CleanImage) -> EncodedImage:
        entry = self.cache.get(image.sha256)
        if entry and time.monotonic() - entry[0] < 300:
            self.cache.move_to_end(image.sha256)
            return replace(entry[1], cached=True, inference_ms=0, model_load_ms=0)
        try:
            # Leave room for lazy CPU imports/model load inside the API's 60s deadline.
            async with httpx.AsyncClient(timeout=55, trust_env=False) as client:
                response = await client.post(
                    f"{self.url}/encode",
                    content=image.content,
                    headers={"Content-Type": "image/png"},
                )
            if response.status_code == 429:
                raise MediaError(429, "Máy đang xử lý ảnh hoặc âm thanh khác. Hãy thử lại sau.")
            if response.status_code != 200:
                raise MediaError(503, "Tìm ảnh cục bộ chưa sẵn sàng. Bạn có thể tìm bằng văn bản.")
            data = response.json()
            vector = tuple(float(v) for v in data["vector"])
            norm = sum(v * v for v in vector)
            if (
                len(vector) != 512
                or data["model_revision"] != CLIP_REVISION
                or not all(math.isfinite(v) for v in vector)
                or not 0.98 < norm < 1.02
            ):
                raise MediaError(
                    503, "Phiên bản vector ảnh không tương thích. Cần tạo lại chỉ mục."
                )
            encoded = EncodedImage(
                vector, CLIP_REVISION, float(data["inference_ms"]), float(data["model_load_ms"])
            )
            self.cache[image.sha256] = (time.monotonic(), encoded)
            while len(self.cache) > 100:
                self.cache.popitem(last=False)
            return encoded
        except (httpx.HTTPError, KeyError, ValueError) as error:
            raise MediaError(
                503, "Không kết nối được mô hình ảnh cục bộ. Hãy tìm bằng văn bản hoặc thử lại."
            ) from error


class HttpTextEncoder:
    def __init__(self, url: str):
        self.url = url
        self.cache: OrderedDict[str, tuple[float, EncodedImage]] = OrderedDict()

    async def encode_text(self, text: str) -> EncodedImage:
        # Hash keys; cache bounded vectors only, never raw user descriptions.
        key = hashlib.sha256(text.encode("utf8")).hexdigest()
        entry = self.cache.get(key)
        if entry and time.monotonic() - entry[0] < 300:
            self.cache.move_to_end(key)
            return replace(entry[1], cached=True, inference_ms=0, model_load_ms=0)
        try:
            async with httpx.AsyncClient(timeout=55, trust_env=False) as client:
                response = await client.post(f"{self.url}/encode-text", json={"text": text})
            if response.status_code == 429:
                raise MediaError(429, "Máy đang xử lý ảnh hoặc giọng nói. Hãy thử lại sau.")
            if response.status_code != 200:
                raise MediaError(503, "Tìm theo mô tả chưa sẵn sàng. Hãy chuyển sang tìm từ khóa.")
            data = response.json()
            vector = tuple(float(v) for v in data["vector"])
            if (
                len(vector) != 512
                or data["model_revision"] != CLIP_REVISION
                or not all(math.isfinite(v) for v in vector)
                or not 0.98 < sum(v * v for v in vector) < 1.02
            ):
                raise MediaError(503, "Vector mô tả không tương thích với chỉ mục ảnh.")
            encoded = EncodedImage(
                vector, CLIP_REVISION, float(data["inference_ms"]), float(data["model_load_ms"])
            )
            self.cache[key] = (time.monotonic(), encoded)
            while len(self.cache) > 100:
                self.cache.popitem(last=False)
            return encoded
        except (httpx.HTTPError, KeyError, ValueError, TypeError) as error:
            raise MediaError(
                503, "Không kết nối được tìm mô tả cục bộ. Hãy dùng tìm từ khóa."
            ) from error


def validate_audio(content: bytes, mime: str, filename: str) -> None:
    if len(content) > 2 * 1024 * 1024:
        raise MediaError(413, "Âm thanh tối đa 2 MB.")
    mime = mime.split(";")[0].strip()
    extension = PurePath(filename.lower()).suffix
    if mime in {"audio/wav", "audio/x-wav"}:
        valid = extension == ".wav" and content.startswith(b"RIFF") and content[8:12] == b"WAVE"
    elif mime == "audio/webm":
        valid = extension == ".webm" and content.startswith(b"\x1aE\xdf\xa3")
    elif mime == "audio/ogg":
        valid = extension == ".ogg" and content.startswith(b"OggS")
    elif mime in {"audio/mp4", "audio/x-m4a"}:
        valid = extension in {".m4a", ".mp4"} and content[4:8] == b"ftyp"
    else:
        valid = False
    if not valid:
        raise MediaError(422, "Chỉ nhận WAV, WebM, Ogg hoặc M4A có nội dung âm thanh hợp lệ.")


class HttpSpeechRecognizer:
    def __init__(self, url: str):
        self.url = url

    async def transcribe(self, content: bytes, mime: str, filename: str) -> Transcript:
        validate_audio(content, mime, filename)
        try:
            async with httpx.AsyncClient(timeout=50, trust_env=False) as client:
                response = await client.post(
                    f"{self.url}/transcribe", content=content, headers={"Content-Type": mime}
                )
            if response.status_code in {413, 422, 429}:
                raise MediaError(
                    response.status_code,
                    str(response.json().get("detail", "Không nhận được âm thanh.")),
                )
            if response.status_code != 200:
                raise MediaError(
                    503, "Nhận giọng nói cục bộ chưa sẵn sàng. Hãy nhập văn bản hoặc thử lại."
                )
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Invalid local recognizer response")
            duration = float(data["duration_seconds"])
            inference_ms, model_load_ms = float(data["inference_ms"]), float(data["model_load_ms"])
            if (
                not isinstance(data["model_revision"], str)
                or data["model_revision"] not in SPEECH_MODELS
                or data["recognizer"] != SPEECH_MODELS.get(data["model_revision"])
                or data["language"] != "vi"
                or not math.isfinite(duration)
                or not 0 < duration <= 15
                or not isinstance(data["text"], str)
                or not 0 < len(data["text"]) <= 2000
                or not all(
                    math.isfinite(value) and value >= 0 for value in (inference_ms, model_load_ms)
                )
                or not isinstance(data["warnings"], list)
                or len(data["warnings"]) > 8
                or not all(isinstance(w, str) and len(w) <= 300 for w in data["warnings"])
            ):
                raise MediaError(
                    503, "Bản ghi từ mô hình không hợp lệ. Hãy nhập văn bản hoặc thử lại."
                )
            return Transcript(
                str(data["text"]),
                str(data["language"]),
                float(data["duration_seconds"]),
                str(data["recognizer"]),
                str(data["model_revision"]),
                inference_ms,
                model_load_ms,
                tuple(str(w) for w in data["warnings"]),
            )
        except (httpx.HTTPError, KeyError, ValueError, TypeError, OverflowError) as error:
            raise MediaError(
                503, "Không kết nối được bộ nhận giọng nói. Bạn có thể nhập văn bản."
            ) from error
