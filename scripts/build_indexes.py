"""Read-only index inventory; use index_images.py for an actual gallery build."""

import argparse
import asyncio
import json

from sqlalchemy import func, select, text

from app.infrastructure.database import engine, session_factory
from app.infrastructure.models import ImageEmbedding, ProductRow


async def plan() -> None:
    async with session_factory() as session:
        extensions = list(
            await session.scalars(text("SELECT extname FROM pg_extension"))
        )
        count = await session.scalar(select(func.count()).select_from(ProductRow))
        vectors = await session.scalar(select(func.count()).select_from(ImageEmbedding))
    await engine.dispose()
    print(
        json.dumps(
            {
                "mode": "plan_only",
                "products": count,
                "extensions": extensions,
                "lexical_index": "Rule/lexical active; normalized shadow; no extra GIN/ANN index",
                "image_embeddings": {
                    "rows": vectors,
                    "build_command": "scripts/index_images.py",
                },
                "text_embeddings": "optional; not built",
                "voice": "Local Whisper adapter implemented; model/health verified separately",
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", action="store_true", required=True)
    parser.parse_args()
    asyncio.run(plan())
