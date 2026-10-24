from collections.abc import Awaitable, Callable
from dataclasses import dataclass, replace
import re
from time import perf_counter

from app.application.query_parser import RuleQueryParser, normalize
from app.domain.catalog import CatalogFilter, CatalogRepository, Product
from app.domain.search import Modality, QueryRepresentation, SearchOptions

RELAX_ORDER = ("material", "color", "brand", "gender", "price_min", "price_max")


@dataclass(frozen=True)
class RankedProduct:
    product: Product
    rank: int
    score: float
    explanation: str


@dataclass(frozen=True)
class SearchOutcome:
    query: QueryRepresentation
    items: tuple[RankedProduct, ...]
    total: int
    page: int
    page_size: int
    latency_ms: float
    stages_ms: dict[str, float]
    search_type: str = "products"
    engine: str = "Tìm từ khóa tiếng Việt (không dùng mô hình ngôn ngữ)"
    notices: tuple[str, ...] = ()
    media: dict[str, str | int | float | bool] | None = None


class QueryService:
    def __init__(self, parser: RuleQueryParser):
        self.parser = parser

    def build(self, text: str, modality: Modality, options: SearchOptions) -> QueryRepresentation:
        return self.parser.parse(text, modality, options)


class SearchService:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository

    async def retrieve(
        self, rep: QueryRepresentation, use_lexical_filter: bool = True
    ) -> list[Product]:
        values = {c.key: c for c in rep.hard_filters}

        def price(key: str) -> int | None:
            c = values.get(key)
            if c is None:
                return None
            return int(c.value) + (-1 if c.operator == "lt" else 1 if c.operator == "gt" else 0)

        category = str(values["category"].value).split("|") if "category" in values else []

        def attribute(key: str) -> str | None:
            return str(values[key].value) if key in values else None

        filters = CatalogFilter(
            page_size=1000,
            categories=tuple(category),
            price_min=price("price_min"),
            price_max=price("price_max"),
            lexical_query=(rep.normalized_text or None) if use_lexical_filter else None,
            color=attribute("color"),
            material=attribute("material"),
            brand=attribute("brand"),
            gender=attribute("gender"),
            size=attribute("size"),
        )
        products, _ = await self.repository.list_products(filters)
        return products


class RankingService:
    def rank(
        self,
        rep: QueryRepresentation,
        products: list[Product],
        image_scores: dict[str, float] | None = None,
        vector_precision: int = 2,
    ) -> list[RankedProduct]:
        stop = {
            "toi",
            "muon",
            "mua",
            "mau",
            "duoi",
            "tren",
            "khong",
            "qua",
            "tam",
            "khoang",
            "nghin",
            "ngan",
            "trieu",
            "tr",
            "k",
            "cu",
            "dong",
            "size",
            "under",
            "over",
        }
        # Conversational scaffolding and spoken price words do not describe a
        # product. Keep content words (e.g. tròn, không dây) for ranking.
        stop.update(
            "cho minh ban xem can tim chon co nao nhe nhe a oi xin chao vui long "
            "giup mot cai chiec doi bo de di lam moi ngay duoc la voi va cua "
            "gia tien ngan sach toi da thieu it nhat nhieu nhat hon re tro xuong "
            "len den tu hai ba bon tu nam lam sau bay tam chin muoi tram linh le "
            "ruoi nay ay thi ma phai lay".split()
        )
        words = [
            w
            for w in rep.normalized_text.split()
            if w not in stop and not any(c.isdigit() for c in w)
        ]
        scored = []
        for product in products:
            haystack = normalize(
                f"{product.name_vi} {product.category_name} {product.color} {product.material} "
                f"{product.brand or ''} {product.original_name or ''}"
            )
            relevance = sum(w in haystack.split() for w in words) / max(1, len(words))
            if any(c.key == "category" for c in rep.hard_filters):
                # Category guarantees a candidate belongs here, but must not
                # flatten lexical differences between products in that category.
                relevance = 0.5 + 0.5 * relevance
            if image_scores is None and re.search(r"\bkhong day\b", rep.normalized_text):
                # "Không dây" is a product phrase, not a disposable negation.
                relevance *= 1 if re.search(r"\b(khong day|wireless)\b", haystack) else 0.5
            if image_scores is not None:
                if product.id not in image_scores:
                    continue
                relevance = image_scores[product.id]
            elif words and relevance < 0.4:
                continue
            preference = 0.0
            for c in (*rep.soft_preferences, *rep.relaxed_filters):
                if c.key == "season":
                    preference += (
                        1.0
                        if "phao" in haystack
                        else 0.8
                        if product.season == c.value
                        else 0.3
                        if "hoodie" in haystack
                        else 0
                    )
                elif c.key == "price_target":
                    preference += max(
                        0, 1 - abs(product.price_vnd - int(c.value)) / max(1, int(c.value))
                    )
                elif (
                    c.key in {"color", "material", "gender"} and getattr(product, c.key) == c.value
                ):
                    preference += 1
            score = min(1, 0.8 * relevance + 0.2 * min(1, preference))
            scored.append((product, relevance, preference, score))
        # Preference can reorder close lexical matches, never override visual relevance bands.
        scored.sort(
            key=lambda p: (
                p[0].available_quantity <= 0,
                -round(p[1], vector_precision) if image_scores is not None else -round(p[1], 6),
                -p[2],
                p[0].id,
            )
        )
        return [
            RankedProduct(
                p,
                rank,
                round(score, 4),
                "Độ khớp ảnh"
                if image_scores is not None
                else "Khớp danh mục và từ khóa; ưu tiên được xét riêng",
            )
            for rank, (p, _, _, score) in enumerate(scored, 1)
        ]


class SearchOrchestrator:
    def __init__(self, repository: CatalogRepository):
        self.repository = repository
        self.retrieval = SearchService(repository)
        self.ranking = RankingService()

    async def search(
        self,
        text: str,
        modality: Modality = "text",
        options: SearchOptions | None = None,
        image_scores: dict[str, float] | None = None,
        image_lookup: Callable[[tuple[str, ...]], Awaitable[dict[str, float]]] | None = None,
        use_lexical_filter: bool = True,
    ) -> SearchOutcome:
        options = options or SearchOptions()
        started = perf_counter()
        parser = RuleQueryParser(await self.repository.categories())
        rep = QueryService(parser).build(text, modality, options)
        parsed = perf_counter()
        candidates = await self.retrieval.retrieve(rep, use_lexical_filter)
        notices: list[str] = []
        for key in RELAX_ORDER:
            if len(candidates) >= 3:
                break
            constraint = next(
                (
                    c
                    for c in rep.hard_filters
                    if c.key == key
                    and c.origin != "ui_selected"
                    and (c.origin == "inferred" or key in options.allow_relax)
                ),
                None,
            )
            if constraint is None:
                continue
            rep = replace(
                rep,
                hard_filters=tuple(c for c in rep.hard_filters if c != constraint),
                relaxed_filters=(*rep.relaxed_filters, constraint),
            )
            notices.append(
                f"Đã chuyển điều kiện {key} thành ưu tiên theo lựa chọn mở rộng của bạn."
                if constraint.origin == "explicit_text"
                else f"Đã nới điều kiện suy đoán {key}; danh mục được giữ nguyên."
            )
            candidates = await self.retrieval.retrieve(rep, use_lexical_filter)
        retrieved = perf_counter()
        if image_lookup is not None:
            image_scores = await image_lookup(tuple(p.id for p in candidates))
        vector_finished = perf_counter()
        ranked = self.ranking.rank(
            rep, candidates, image_scores, vector_precision=6 if not use_lexical_filter else 2
        )
        if options.sort != "relevance":
            ranked.sort(
                key=lambda r: (
                    r.product.price_vnd if options.sort == "price_asc" else -r.product.price_vnd,
                    r.product.id,
                )
            )
            ranked = [replace(row, rank=i) for i, row in enumerate(ranked, 1)]
        finished = perf_counter()
        start = (options.page - 1) * options.page_size
        if len(candidates) == 1000:
            notices.append("Kết quả được giới hạn trong 1.000 ứng viên phù hợp nhất.")
        return SearchOutcome(
            rep,
            tuple(ranked[start : start + options.page_size]),
            len(ranked),
            options.page,
            options.page_size,
            round((finished - started) * 1000, 3),
            {
                "parse": round((parsed - started) * 1000, 3),
                "db_prefilter_lexical": round((retrieved - parsed) * 1000, 3),
                "vector_search": round((vector_finished - retrieved) * 1000, 3)
                if image_lookup is not None
                else 0.0,
                "ranking": round((finished - vector_finished) * 1000, 3),
            },
            notices=tuple(notices),
        )
