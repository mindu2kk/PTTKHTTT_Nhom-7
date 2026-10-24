import unicodedata
from dataclasses import replace

from app.application.speech_context import (
    SpeechVocabularyEntry,
    product_alternatives,
    public_product_vocabulary,
)
from app.domain.catalog import CatalogFilter, CatalogRepository
from app.domain.media import MediaError, SpeechRecognizer, Transcript


class SpeechService:
    def __init__(self, recognizer: SpeechRecognizer, catalog: CatalogRepository | None = None):
        self.recognizer = recognizer
        self.catalog = catalog

    async def transcribe(self, content: bytes, mime: str, filename: str) -> Transcript:
        result = await self.recognizer.transcribe(content, mime, filename)
        text = " ".join(unicodedata.normalize("NFC", result.text).split())
        if not text:
            raise MediaError(422, "Chưa nghe rõ câu nói. Hãy ghi lại một câu ngắn.")
        if len(text) > 300:
            raise MediaError(422, "Câu nhận được quá dài. Hãy ghi ngắn hơn, tối đa 300 ký tự.")
        vocabulary: tuple[SpeechVocabularyEntry, ...] = ()
        warnings = result.warnings
        if self.catalog is not None:
            try:
                products, _ = await self.catalog.list_products(CatalogFilter(page_size=1000))
                vocabulary = public_product_vocabulary(products)
            except Exception:
                # Catalog suggestions are optional; the actual recognizer text must
                # remain usable when the catalog is temporarily unavailable.
                warnings = (
                    *warnings,
                    "Gợi ý tên sản phẩm tạm chưa sẵn sàng. Hãy kiểm tra câu đã nhận.",
                )
        return replace(
            result,
            text=text,
            warnings=warnings,
            suggestions=product_alternatives(text, vocabulary),
        )
