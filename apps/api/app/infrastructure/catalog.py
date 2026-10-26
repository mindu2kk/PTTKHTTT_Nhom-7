from dataclasses import replace
from typing import Any

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.catalog import CatalogFilter, Category, Product
from app.infrastructure.models import (
    CategoryRow,
    DataSource,
    Inventory,
    ProductAttribute,
    ProductImage,
    ProductRow,
    ProductSize,
    ProductSource,
    ProductVariant,
    SellerOffer,
)


class SqlCatalogRepository:
    def __init__(self, session: AsyncSession, profile: str):
        self.session = session
        self.profile = profile

    async def categories(self) -> list[Category]:
        rows = (
            await self.session.scalars(
                select(CategoryRow)
                .where(CategoryRow.is_active.is_(True))
                .order_by(CategoryRow.level, CategoryRow.sort_order, CategoryRow.id)
            )
        ).all()
        return [Category(r.id, r.parent_id, r.slug, r.name_vi, r.level, r.sort_order) for r in rows]

    async def _products(
        self, filters: CatalogFilter, identifier: str | None = None
    ) -> tuple[list[Product], int]:
        material = (
            select(
                ProductAttribute.product_id,
                ProductAttribute.display_value_vi.label("material"),
            )
            .where(
                ProductAttribute.attribute_key == "material",
                ProductAttribute.review_status == "verified",
            )
            .subquery()
        )
        source = (
            select(
                ProductSource.product_id,
                func.coalesce(
                    func.min(DataSource.id).filter(DataSource.id.like("operator-public-%")),
                    func.min(DataSource.id),
                ).label("source_id"),
                func.min(DataSource.rights_status).label("rights_status"),
            )
            .join(DataSource, DataSource.id == ProductSource.source_id)
            .group_by(ProductSource.product_id)
            .subquery()
        )
        safe_rights = ["demo"] if self.profile == "demo_seed" else ["approved"]
        season = (
            select(ProductAttribute.product_id, ProductAttribute.display_value_vi.label("season"))
            .where(
                ProductAttribute.attribute_key == "season",
                ProductAttribute.review_status == "verified",
            )
            .subquery()
        )
        # Independent non-null ID set: PostgreSQL can hash rights failures once,
        # instead of probing every source for every candidate in a correlated anti-join.
        unsafe_source = (
            select(ProductSource.product_id)
            .join(DataSource, DataSource.id == ProductSource.source_id)
            .where(
                DataSource.rights_status.not_in(safe_rights),
            )
        )
        query = (
            select(
                ProductRow.id,
                ProductRow.slug,
                ProductRow.name_vi,
                ProductRow.description_vi,
                ProductRow.category_id,
                CategoryRow.name_vi.label("category_name"),
                SellerOffer.price_vnd,
                (Inventory.on_hand - Inventory.reserved).label("available_quantity"),
                ProductImage.storage_key.label("image_url"),
                ProductImage.alt_vi.label("image_alt"),
                ProductVariant.color,
                func.coalesce(material.c.material, "Chưa có thông tin").label("material"),
                ProductVariant.size,
                ProductRow.gender,
                ProductRow.verification_status,
                SellerOffer.price_kind,
                source.c.source_id,
                source.c.rights_status,
                ProductRow.data_profile,
                ProductRow.brand_id.label("brand"),
                ProductRow.original_name,
                season.c.season,
            )
            .join(CategoryRow, CategoryRow.id == ProductRow.category_id)
            .join(ProductVariant, ProductVariant.product_id == ProductRow.id)
            .join(
                SellerOffer,
                # Composite FK (variant_id, product_id) enforces product identity.
                # Repeating both equality predicates hid that dependency from the
                # planner (estimated 1 vs 3000 rows, thousands of nested probes).
                SellerOffer.variant_id == ProductVariant.id,
            )
            .join(Inventory, Inventory.offer_id == SellerOffer.id)
            .join(ProductImage, ProductImage.product_id == ProductRow.id)
            .join(source, source.c.product_id == ProductRow.id)
            .outerjoin(material, material.c.product_id == ProductRow.id)
            .outerjoin(season, season.c.product_id == ProductRow.id)
            .where(
                CategoryRow.is_active.is_(True),
                ProductRow.publication_status == "published",
                ProductRow.verification_status == "verified",
                ProductRow.data_profile == self.profile,
                ProductRow.id.not_in(unsafe_source),
                ProductImage.license_status.in_(safe_rights),
                ProductImage.is_primary.is_(True),
                ProductVariant.status == "active",
                SellerOffer.active.is_(True),
                SellerOffer.seller_verified.is_(True),
                SellerOffer.price_kind
                == ("merchant_verified" if self.profile == "approved_public" else "demo"),
            )
        )
        if identifier is not None:
            query = query.where(or_(ProductRow.id == identifier, ProductRow.slug == identifier))
        if filters.category or filters.categories:
            selected = list(filters.categories) or (
                [filters.category] if filters.category is not None else []
            )
            tree = (
                select(CategoryRow.id)
                .where(or_(CategoryRow.id.in_(selected), CategoryRow.slug.in_(selected)))
                .cte("category_tree", recursive=True)
            )
            # UNION also prevents duplicate results for overlapping selected subtrees.
            tree = tree.union(select(CategoryRow.id).join(tree, CategoryRow.parent_id == tree.c.id))
            query = query.join(tree, ProductRow.category_id == tree.c.id)
        if filters.price_min is not None:
            query = query.where(SellerOffer.price_vnd >= filters.price_min)
        if filters.price_max is not None:
            query = query.where(SellerOffer.price_vnd <= filters.price_max)
        if filters.color:
            query = query.where(ProductVariant.color == filters.color)
        if filters.gender:
            query = query.where(ProductRow.gender == filters.gender)
        if filters.material:
            query = query.where(material.c.material == filters.material)
        if filters.brand:
            query = query.where(ProductRow.brand_id == filters.brand)
        if filters.size:
            query = query.where(
                ProductRow.id.in_(
                    select(ProductSize.product_id).where(ProductSize.size == filters.size)
                )
            )
        if filters.available:
            query = query.where(Inventory.on_hand > Inventory.reserved)
        total = int(
            (await self.session.scalar(select(func.count()).select_from(query.subquery()))) or 0
        )
        orderings: dict[str, ColumnElement[Any]] = {
            "price_asc": SellerOffer.price_vnd.asc(),
            "price_desc": SellerOffer.price_vnd.desc(),
            "newest": ProductRow.created_at.desc(),
        }
        ordering = orderings[filters.sort]
        if filters.lexical_query:
            ordering = func.similarity(
                ProductRow.search_text_normalized, filters.lexical_query
            ).desc()
        rows = (
            (
                await self.session.execute(
                    query.order_by(ordering, ProductRow.id)
                    .offset((filters.page - 1) * filters.page_size)
                    .limit(filters.page_size)
                )
            )
            .mappings()
            .all()
        )
        return [Product(**dict(row)) for row in rows], total

    async def list_products(self, filters: CatalogFilter) -> tuple[list[Product], int]:
        return await self._products(filters)

    async def facets(self) -> dict[str, list[str]]:
        # Same publication/rights gate as catalog; bounded to the documented <=5k demo.
        products, _ = await self._products(CatalogFilter(page_size=5000))
        brands = (
            await self.session.scalars(
                select(ProductRow.brand_id)
                .where(
                    ProductRow.id.in_([p.id for p in products]), ProductRow.brand_id.is_not(None)
                )
                .distinct()
            )
        ).all()
        result = {
            key: sorted(
                {
                    str(getattr(p, key))
                    for p in products
                    if getattr(p, key) and getattr(p, key) != "Chưa có thông tin"
                }
            )
            for key in ["color", "material", "gender", "size"]
        }
        result["size"] = sorted(
            (
                await self.session.scalars(
                    select(ProductSize.size)
                    .where(ProductSize.product_id.in_([p.id for p in products]))
                    .distinct()
                )
            ).all()
        )
        result["brand"] = sorted(b for b in brands if b)
        return result

    async def get_product(self, identifier: str) -> Product | None:
        products, _ = await self._products(CatalogFilter(page_size=1), identifier)
        if not products:
            return None
        product = products[0]
        images = (
            await self.session.scalars(
                select(ProductImage)
                .where(
                    ProductImage.product_id == product.id,
                    ProductImage.license_status
                    == ("demo" if self.profile == "demo_seed" else "approved"),
                )
                .order_by(ProductImage.is_primary.desc(), ProductImage.sort_order, ProductImage.id)
            )
        ).all()
        sizes = (
            await self.session.scalars(
                select(ProductSize)
                .where(ProductSize.product_id == product.id)
                .order_by(ProductSize.id)
            )
        ).all()
        return replace(
            product,
            sizes=tuple(
                {
                    "id": size.id,
                    "size": size.size,
                    "available_quantity": min(
                        size.stock_quantity - size.reserved, product.available_quantity
                    ),
                }
                for size in sizes
            ),
            images=tuple(
                {
                    "url": image.storage_key,
                    "alt": image.alt_vi,
                    "width": image.width,
                    "height": image.height,
                }
                for image in images
            ),
        )
