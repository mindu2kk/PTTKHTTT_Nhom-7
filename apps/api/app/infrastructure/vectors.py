from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models import ImageEmbedding, ProductImage


class SqlImageVectorIndex:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self, vector: tuple[float, ...], revision: str, allowed: tuple[str, ...]
    ) -> dict[str, float]:
        if not allowed:
            return {}
        distance = ImageEmbedding.embedding.cosine_distance(list(vector))
        query = (
            select(ProductImage.product_id, func.min(distance).label("distance"))
            .join(ImageEmbedding, ImageEmbedding.image_id == ProductImage.id)
            .where(
                ProductImage.product_id.in_(allowed),
                ProductImage.license_status.in_(["demo", "approved"]),
                ImageEmbedding.model_revision == revision,
                ImageEmbedding.model_name == "OpenCLIP ViT-B/32",
                ImageEmbedding.content_hash == ProductImage.sha256,
            )
            .group_by(ProductImage.product_id)
            .order_by(func.min(distance), ProductImage.product_id)
            .limit(1000)
        )
        rows = (await self.session.execute(query)).all()
        return {str(pid): max(0, min(1, (2 - float(dist)) / 2)) for pid, dist in rows}
