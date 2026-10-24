from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.v1.catalog import ProductResponse
from app.api.v1.search import SearchRequest, SearchResponse
from app.application.shopping_assistant import ShoppingAssistant
from app.core.dependencies import shopping_assistant
from app.domain.media import MediaError
from app.domain.search import SearchOptions

router = APIRouter(prefix="/api/v1/search", tags=["Hỗ trợ chọn sản phẩm"])
Service = Annotated[ShoppingAssistant, Depends(shopping_assistant)]


class DescribeRequest(SearchRequest):
    mode: Literal["keyword", "visual"] = "visual"


@router.post("/describe", response_model=SearchResponse)
async def describe(body: DescribeRequest, service: Service) -> SearchResponse:
    try:
        options = SearchOptions(**body.model_dump(exclude={"q", "modality", "mode"}))
        result = await service.describe(body.q, options, body.mode == "visual")
        return SearchResponse.model_validate(result)
    except MediaError as error:
        raise HTTPException(error.status, error.message) from error


class CompareRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[str] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def valid_ids(self) -> "CompareRequest":
        if len(set(self.ids)) != len(self.ids) or any(not 1 <= len(i) <= 100 for i in self.ids):
            raise ValueError("invalid comparison")
        return self


class CompareResponse(BaseModel):
    products: list[ProductResponse]
    lowest_price_ids: list[str]
    notice: str


@router.post("/compare", response_model=CompareResponse)
async def compare(body: CompareRequest, service: Service) -> CompareResponse:
    try:
        products = await service.compare(tuple(body.ids))
        lowest = min(p.price_vnd for p in products)
        return CompareResponse(
            products=[ProductResponse.model_validate(p) for p in products],
            lowest_price_ids=[p.id for p in products if p.price_vnd == lowest],
            notice=(
                "So sánh thuộc tính công khai hiện tại; giá và hạn mức đặt thử mô phỏng. "
                "Không có dữ liệu đánh giá, độ bền hay hiệu năng để kết luận sản phẩm tốt nhất."
            ),
        )
    except MediaError as error:
        raise HTTPException(error.status, error.message) from error
