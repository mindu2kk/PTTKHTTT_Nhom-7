from dataclasses import dataclass
from typing import Protocol


class MediaError(Exception):
    def __init__(self, status: int, message: str):
        self.status = status
        self.message = message
        super().__init__(message)


@dataclass(frozen=True)
class CleanImage:
    content: bytes
    sha256: str
    width: int
    height: int


@dataclass(frozen=True)
class EncodedImage:
    vector: tuple[float, ...]
    revision: str
    inference_ms: float
    model_load_ms: float
    cached: bool = False


class MediaValidator(Protocol):
    async def clean_image(self, content: bytes, mime: str, filename: str) -> CleanImage: ...


class LocalImageEncoder(Protocol):
    async def encode(self, image: CleanImage) -> EncodedImage: ...


class LocalTextEncoder(Protocol):
    async def encode_text(self, text: str) -> EncodedImage: ...


class ImageVectorIndex(Protocol):
    async def search(
        self, vector: tuple[float, ...], revision: str, allowed: tuple[str, ...]
    ) -> dict[str, float]: ...


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str
    duration_seconds: float
    recognizer: str
    model_revision: str
    inference_ms: float
    model_load_ms: float
    warnings: tuple[str, ...]
    suggestions: tuple[str, ...] = ()


class SpeechRecognizer(Protocol):
    async def transcribe(self, content: bytes, mime: str, filename: str) -> Transcript: ...
