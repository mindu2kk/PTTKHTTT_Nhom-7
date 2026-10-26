from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.application.catalog import ProductService
from app.core.dependencies import product_service
from app.domain.catalog import CatalogFilter

router = APIRouter(prefix="/api/v1", tags=["Danh mục"])
Service = Annotated[ProductService, Depends(product_service)]


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    parent_id: str | None
    slug: str
    name_vi: str
    level: int
    sort_order: int


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    slug: str
    name_vi: str
    description_vi: str
    category_id: str
    category_name: str
    price_vnd: int
    available_quantity: int
    image_url: str
    image_alt: str
    color: str
    material: str
    size: str
    gender: str | None
    verification_status: str
    price_kind: str
    source_id: str
    rights_status: str
    data_profile: str
    season: str | None = None
    data_notice: str = "dữ liệu mô phỏng"
    brand: str | None = None
    original_name: str | None = None
    images: tuple[dict[str, str | int], ...] = ()
    sizes: tuple[dict[str, str | int], ...] = ()

    @model_validator(mode="after")
    def public_notice(self) -> "ProductResponse":
        if self.data_profile == "real_demo":
            source = {
                "amazon-berkeley-objects": "ABO",
                "rhodi-user-reviewed": "Rhodi",
            }.get(self.source_id, "nguồn đã duyệt")
            self.data_notice = f"Sản phẩm và ảnh từ {source} · Giá và hạn mức đặt thử mô phỏng"
        elif self.data_profile != "demo_seed":
            self.data_notice = "Dữ liệu đã được duyệt"
        return self


class ProductPage(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int


class ProductQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page: int = Field(1, ge=1, le=10000)
    page_size: int = Field(12, ge=1, le=24)
    category: str | None = Field(None, max_length=100)
    price_min: int | None = Field(None, ge=0, le=1_000_000_000_000)
    price_max: int | None = Field(None, ge=0, le=1_000_000_000_000)
    color: str | None = Field(None, max_length=40)
    gender: str | None = Field(None, max_length=30)
    material: str | None = Field(None, max_length=100)
    brand: str | None = Field(None, max_length=80)
    size: str | None = Field(None, max_length=30)
    available: bool = False
    sort: Literal["newest", "price_asc", "price_desc"] = "newest"

    @model_validator(mode="after")
    def valid_range(self) -> "ProductQuery":
        if (
            self.price_min is not None
            and self.price_max is not None
            and self.price_min > self.price_max
        ):
            raise ValueError("invalid price range")
        return self


@router.get("/categories", response_model=list[CategoryResponse])
async def categories(service: Service) -> list[CategoryResponse]:
    return [CategoryResponse.model_validate(c) for c in await service.categories()]


@router.get("/products", response_model=ProductPage)
async def products(service: Service, query: Annotated[ProductQuery, Query()]) -> ProductPage:
    items, total = await service.list_products(CatalogFilter(**query.model_dump()))
    return ProductPage(
        items=[ProductResponse.model_validate(p) for p in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
    )


@router.get("/facets")
async def facets(service: Service) -> dict[str, list[str]]:
    return await service.facets()


@router.get("/products/{id_or_slug}", response_model=ProductResponse)
async def product(id_or_slug: str, service: Service) -> ProductResponse:
    if len(id_or_slug) > 180:
        raise HTTPException(404, "Không tìm thấy sản phẩm.")
    item = await service.get_product(id_or_slug)
    if item is None:
        raise HTTPException(404, "Không tìm thấy sản phẩm.")
    return ProductResponse.model_validate(item)
