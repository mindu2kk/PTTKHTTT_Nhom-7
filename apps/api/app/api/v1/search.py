import re
from typing import Annotated, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.catalog import ProductResponse
from app.api.v1.commerce import OrderResponse, optional_actor
from app.application.commerce import CommerceService
from app.application.query_parser import ORDER_INTENT, normalize
from app.application.search import SearchOrchestrator, SearchOutcome
from app.core.dependencies import commerce_service, search_service
from app.domain.commerce import Actor
from app.domain.search import SearchOptions, SearchRecord, SearchRecordItem

router = APIRouter(prefix="/api/v1/search", tags=["Tìm kiếm"])
Service = Annotated[SearchOrchestrator, Depends(search_service)]


class SearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    q: str = Field(min_length=1, max_length=300)
    modality: Literal["text", "voice"] = "text"
    category: str | None = Field(None, max_length=100)
    price_min: int | None = Field(None, ge=0, le=10**12)
    price_max: int | None = Field(None, ge=0, le=10**12)
    color: str | None = Field(None, max_length=40)
    material: str | None = Field(None, max_length=100)
    brand: str | None = Field(None, max_length=80)
    gender: str | None = Field(None, max_length=30)
    page: int = Field(1, ge=1, le=1000)
    page_size: int = Field(12, ge=1, le=24)
    sort: Literal["relevance", "price_asc", "price_desc"] = "relevance"
    allow_relax: list[Literal["color", "material", "brand", "gender", "price_min", "price_max"]] = (
        Field(default_factory=list, max_length=6)
    )

    @model_validator(mode="after")
    def valid_prices(self) -> "SearchRequest":
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("invalid range")
        return self


class ConstraintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    key: str
    value: str | int
    origin: str
    confidence: float
    operator: str


class QueryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    modality: str
    raw_text: str
    normalized_text: str
    hard_filters: list[ConstraintResponse]
    soft_preferences: list[ConstraintResponse]
    relaxed_filters: list[ConstraintResponse]


class RankedResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    product: ProductResponse
    rank: int
    score: float
    explanation: str


class SearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    search_type: Literal["products"] = "products"
    query: QueryResponse
    items: list[RankedResponse]
    total: int
    page: int
    page_size: int
    latency_ms: float
    stages_ms: dict[str, float]
    engine: str
    notices: list[str]
    media: dict[str, str | int | float | bool] | None = None


class OrderSearchResponse(BaseModel):
    search_type: Literal["order"] = "order"
    order: OrderResponse


async def remember_safely(commerce: CommerceService, actor: Actor, result: SearchOutcome) -> None:
    try:
        await commerce.remember(
            actor,
            SearchRecord(
                result.query,
                tuple(
                    SearchRecordItem(
                        row.product.id,
                        row.rank,
                        row.score,
                        row.explanation,
                        row.relevance_score,
                        row.preference_score,
                    )
                    for row in result.items
                ),
            ),
        )
    except Exception:
        # History is optional; never expose bodies or interrupt a successful search.
        return


async def execute(
    body: SearchRequest,
    service: SearchOrchestrator,
    actor: Actor | None,
    commerce: CommerceService,
    tasks: BackgroundTasks,
) -> SearchResponse | OrderSearchResponse:
    if ORDER_INTENT.search(normalize(body.q)):
        if not actor:
            raise HTTPException(401, "Đăng nhập để tra cứu đơn hàng của bạn.")
        code = re.search(r"\b(HM[a-fA-F0-9]{14}|\d{6,20})\b", body.q, re.I)
        if not code:
            raise HTTPException(422, "Hãy nhập mã đơn hàng cần tra cứu.")
        return OrderSearchResponse(
            order=OrderResponse.model_validate(await commerce.order(actor, code[0].upper()))
        )
    values = body.model_dump(exclude={"q", "modality"})
    values["allow_relax"] = tuple(values["allow_relax"])
    outcome = await service.search(body.q, body.modality, SearchOptions(**values))
    result = SearchResponse.model_validate(outcome)
    if actor:
        tasks.add_task(remember_safely, commerce, actor, outcome)
    return result


@router.get("/text", response_model=SearchResponse | OrderSearchResponse)
async def text_get(
    service: Service,
    body: Annotated[SearchRequest, Query()],
    actor: Annotated[Actor | None, Depends(optional_actor)],
    commerce: Annotated[CommerceService, Depends(commerce_service)],
    tasks: BackgroundTasks,
) -> SearchResponse | OrderSearchResponse:
    return await execute(body, service, actor, commerce, tasks)


@router.post("/text", response_model=SearchResponse | OrderSearchResponse)
async def text_post(
    body: SearchRequest,
    service: Service,
    actor: Annotated[Actor | None, Depends(optional_actor)],
    commerce: Annotated[CommerceService, Depends(commerce_service)],
    tasks: BackgroundTasks,
) -> SearchResponse | OrderSearchResponse:
    return await execute(body, service, actor, commerce, tasks)


@router.get("/suggestions")
async def suggestions(
    service: Service, q: str = Query(min_length=2, max_length=100)
) -> dict[str, list[str]]:
    result = await service.search(q, options=SearchOptions(page_size=5))
    return {"suggestions": [item.product.name_vi for item in result.items]}
