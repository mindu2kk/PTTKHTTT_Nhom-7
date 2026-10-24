from app.domain.catalog import CatalogFilter, CatalogRepository, Category, Product


class ProductService:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    async def categories(self) -> list[Category]:
        return await self.repository.categories()

    async def facets(self) -> dict[str, list[str]]:
        return await self.repository.facets()

    async def list_products(self, filters: CatalogFilter) -> tuple[list[Product], int]:
        return await self.repository.list_products(filters)

    async def get_product(self, identifier: str) -> Product | None:
        return await self.repository.get_product(identifier)
