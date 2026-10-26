from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.sizes import product_sizes
from app.infrastructure.models import Inventory, ProductSize, ProductVariant, SellerOffer


async def initialize_sizes(session: AsyncSession, product_id: str) -> None:
    """Allocate existing demo capacity once, without changing its total."""
    await session.flush()
    if await session.scalar(select(ProductSize.id).where(ProductSize.product_id == product_id)):
        return
    row = (
        await session.execute(
            select(ProductVariant, Inventory)
            .join(SellerOffer, SellerOffer.variant_id == ProductVariant.id)
            .join(Inventory, Inventory.offer_id == SellerOffer.id)
            .where(ProductVariant.product_id == product_id)
        )
    ).one()
    variant, stock = row
    sizes = product_sizes(variant.size)
    remaining = stock.on_hand - stock.reserved
    for index, size in enumerate(sizes):
        held = stock.reserved if index == 0 else 0
        session.add(
            ProductSize(
                product_id=product_id,
                size=size,
                stock_quantity=held + remaining // len(sizes) + (index < remaining % len(sizes)),
                reserved=held,
            )
        )
    await session.flush()
