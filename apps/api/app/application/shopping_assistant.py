"""Grounded catalog tools; visual descriptions use the existing local CLIP text tower."""

import re
from dataclasses import replace
from time import perf_counter

from app.application.query_parser import ORDER_INTENT, normalize
from app.application.search import SearchOrchestrator, SearchOutcome
from app.domain.catalog import Product
from app.domain.media import ImageVectorIndex, LocalTextEncoder, MediaError
from app.domain.search import SearchOptions

# This is a finite concept mapping, not machine translation or an LLM.
CONCEPTS = {
    "giay the thao": "sneakers",
    "sneaker": "sneakers",
    "giay": "shoes",
    "dep": "sandals",
    "sofa": "sofa",
    "ghe": "chair",
    "ban phim": "computer keyboard",
    "ban": "table",
    "tai nghe": "headphones",
    "loa": "speaker",
    "den ban": "desk lamp",
    "den": "lamp",
    "tham": "rug",
    "goi": "pillow",
    "coc": "mug",
    "chao": "frying pan",
    "may pha": "coffee maker",
    "op lung": "phone case",
    "bo sac": "charger",
    "chuot": "computer mouse",
    "dung cu bep": "kitchen utensils",
    "cho ngoi": "chair",
    "do chieu sang": "desk lamp",
    "do lot san": "rug",
    "do tua dau": "pillow",
    "vo bao ve dien thoai": "phone case",
    "do mang chan": "shoes",
}
DESCRIPTORS = {
    "xanh duong": "blue",
    "xanh la": "green",
    "xanh than": "navy blue",
    "den": "black",
    "trang": "white",
    "do": "red",
    "vang": "yellow",
    "hong": "pink",
    "mau tim": "purple",
    "nau": "brown",
    "xam": "gray",
    "be": "beige",
    "go": "wooden",
    "boc da": "leather",
    "vai": "fabric",
    "tron": "round",
    "vuong": "square",
    "the thao": "sporty",
    "toi gian": "minimalist",
    "nam": "for men",
    "nu": "for women",
}


def visual_prompt(text: str) -> str | None:
    value = normalize(text)
    matches = [
        (key, english)
        for key, english in CONCEPTS.items()
        if re.search(rf"\b{re.escape(key)}\b", value)
    ]
    if not matches:
        return None
    concept, english = max(matches, key=lambda item: len(item[0]))
    remaining = re.sub(rf"\b{re.escape(concept)}\b", " ", value)
    # Price phrases and their numbers are filters, never visual descriptors.
    remaining = re.sub(
        r"\b(?:toi da|khong qua|duoi|tren|tu|tam|khoang)\s+\S+"
        r"(?:\s+(?:tram|muoi|nghin|ngan|trieu))?",
        " ",
        remaining,
    )
    words = []
    for key, description in sorted(DESCRIPTORS.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(key)}\b", remaining):
            words.append(description)
            remaining = re.sub(rf"\b{re.escape(key)}\b", " ", remaining)
    return f"a product photo of {' '.join(words)} {english}".replace("  ", " ")


class ShoppingAssistant:
    def __init__(
        self, search: SearchOrchestrator, encoder: LocalTextEncoder, index: ImageVectorIndex
    ):
        self.search = search
        self.encoder = encoder
        self.index = index

    async def describe(self, text: str, options: SearchOptions, visual: bool) -> SearchOutcome:
        started = perf_counter()
        if ORDER_INTENT.search(normalize(text)):
            raise MediaError(422, "Để xem đơn của bạn, hãy mở mục Đơn hàng và đăng nhập.")
        if not visual:
            return await self.search.search(text, options=options)
        prompt = visual_prompt(text)
        if prompt is None:
            raise MediaError(
                422,
                "Chưa hiểu loại sản phẩm trong mô tả. Hãy nêu tên như giày, ghế, sofa, "
                "đèn bàn hoặc ốp lưng; hoặc chuyển sang tìm từ khóa.",
            )
        encoded = await self.encoder.encode_text(prompt)

        async def lookup(allowed: tuple[str, ...]) -> dict[str, float]:
            return await self.index.search(encoded.vector, encoded.revision, allowed)

        result = await self.search.search(
            text, options=options, image_lookup=lookup, use_lexical_filter=False
        )
        return replace(
            result,
            latency_ms=round((perf_counter() - started) * 1000, 3),
            items=tuple(
                replace(row, explanation="Mức tương tự giữa mô tả và ảnh; không phải xác suất đúng")
                for row in result.items
            ),
            engine="OpenCLIP ViT-B/32 text → ảnh, CPU cục bộ",
            stages_ms={
                **result.stages_ms,
                "text_embed": encoded.inference_ms,
                "model_load": encoded.model_load_ms,
            },
            notices=(
                *result.notices,
                "Mô tả Việt dùng bộ từ vựng hữu hạn, không dùng chatbot sinh nội dung. "
                "Giá và hạn mức đặt thử được mô phỏng; hãy kiểm tra thuộc tính ở trang chi tiết.",
            ),
            media={
                "model_revision": encoded.revision,
                "model_name": "OpenCLIP ViT-B/32",
                "visual_prompt": prompt,
                "cached": encoded.cached,
                "temporary_only": True,
            },
        )

    async def compare(self, ids: tuple[str, ...]) -> list[Product]:
        products = []
        for identifier in ids:
            product = await self.search.repository.get_product(identifier)
            if product is None:
                # Do not distinguish unpublished/rights-revoked/missing records.
                raise MediaError(
                    404, "Có sản phẩm không còn trong danh mục công khai. Hãy chọn lại."
                )
            products.append(product)
        return products
