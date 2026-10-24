from dataclasses import replace
from time import perf_counter

from app.application.search import SearchOrchestrator, SearchOutcome
from app.domain.media import ImageVectorIndex, LocalImageEncoder, MediaValidator
from app.domain.search import SearchOptions


class ImageSearchService:
    def __init__(
        self,
        search: SearchOrchestrator,
        validator: MediaValidator,
        encoder: LocalImageEncoder,
        index: ImageVectorIndex,
    ):
        self.search = search
        self.validator = validator
        self.encoder = encoder
        self.index = index

    async def find(
        self, raw: bytes, mime: str, filename: str, text: str, options: SearchOptions
    ) -> SearchOutcome:
        start = perf_counter()
        image = await self.validator.clean_image(raw, mime, filename)
        validated = perf_counter()
        encoded = await self.encoder.encode(image)
        encoded_at = perf_counter()

        async def lookup(allowed: tuple[str, ...]) -> dict[str, float]:
            return await self.index.search(encoded.vector, encoded.revision, allowed)

        result = await self.search.search(text, "image", options, image_lookup=lookup)
        return replace(
            result,
            query=replace(result.query, image_vector_ref=encoded.revision),
            latency_ms=round((perf_counter() - start) * 1000, 3),
            stages_ms={
                **result.stages_ms,
                "input_validation": round((validated - start) * 1000, 3),
                "image_embed": encoded.inference_ms,
                "image_encoder_http": round((encoded_at - validated) * 1000, 3),
                "model_load": encoded.model_load_ms,
            },
            engine="OpenCLIP ViT-B/32 cục bộ · so sánh cosine chính xác trong sản phẩm đã lọc",
            media={
                "sha256": image.sha256,
                "width": image.width,
                "height": image.height,
                "model_revision": encoded.revision,
                "model_name": "OpenCLIP ViT-B/32",
                "cached": encoded.cached,
                "temporary_only": True,
            },
        )
