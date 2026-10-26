from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass(frozen=True)
class Category:
    id: str
    parent_id: str | None
    slug: str
    name_vi: str
    level: int
    sort_order: int


@dataclass(frozen=True)
class Product:
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
    brand: str | None = None
    original_name: str | None = None
    images: tuple[dict[str, str | int], ...] = ()
    sizes: tuple[dict[str, str | int], ...] = ()


@dataclass(frozen=True)
class CatalogFilter:
    page: int = 1
    page_size: int = 12
    category: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    color: str | None = None
    gender: str | None = None
    sort: Literal["newest", "price_asc", "price_desc"] = "newest"
    categories: tuple[str, ...] = ()
    material: str | None = None
    brand: str | None = None
    lexical_query: str | None = None
    size: str | None = None
    available: bool = False


class CatalogRepository(Protocol):
    async def facets(self) -> dict[str, list[str]]: ...
    async def categories(self) -> list[Category]: ...

    async def list_products(self, filters: CatalogFilter) -> tuple[list[Product], int]: ...

    async def get_product(self, identifier: str) -> Product | None: ...
