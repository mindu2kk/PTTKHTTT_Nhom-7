from dataclasses import dataclass, field
from typing import Literal, Protocol

Modality = Literal["text", "voice", "image"]
Origin = Literal["ui_selected", "explicit_text", "inferred"]
Operator = Literal["eq", "lt", "lte", "gt", "gte", "any"]


@dataclass(frozen=True)
class FilterConstraint:
    key: str
    value: str | int
    origin: Literal["ui_selected", "explicit_text", "inferred"]
    confidence: float
    operator: Literal["eq", "lt", "lte", "gt", "gte", "any"] = "eq"


@dataclass(frozen=True)
class QueryRepresentation:
    modality: Literal["text", "voice", "image"]
    raw_text: str = ""
    normalized_text: str = ""
    image_vector_ref: str | None = None
    hard_filters: tuple[FilterConstraint, ...] = field(default_factory=tuple)
    soft_preferences: tuple[FilterConstraint, ...] = field(default_factory=tuple)
    relaxed_filters: tuple[FilterConstraint, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SearchOptions:
    category: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    color: str | None = None
    material: str | None = None
    brand: str | None = None
    gender: str | None = None
    page: int = 1
    page_size: int = 12
    sort: Literal["relevance", "price_asc", "price_desc"] = "relevance"
    allow_relax: tuple[str, ...] = ()
    top_k: int | None = None


@dataclass(frozen=True)
class SearchRecordItem:
    product_id: str
    rank: int
    score: float
    explanation: str
    relevance_score: float = 0.0
    preference_score: float = 0.0


@dataclass(frozen=True)
class SearchRecord:
    query: QueryRepresentation
    items: tuple[SearchRecordItem, ...]


class QueryParser(Protocol):
    def parse(self, text: str, modality: Modality) -> QueryRepresentation: ...


class SpeechToText(Protocol):
    async def transcribe(self, audio: bytes, mime: str) -> str: ...


class ImageEncoder(Protocol):
    def encode(self, image: bytes) -> tuple[float, ...]: ...


class KeywordIndex(Protocol):
    async def retrieve(self, query: QueryRepresentation, limit: int) -> list[tuple[str, float]]: ...


class VectorIndex(Protocol):
    async def retrieve(
        self, vector: tuple[float, ...], model_revision: str, limit: int
    ) -> list[tuple[str, float]]: ...
