"""Deterministic Vietnamese parsing; all shadow normalization preserves original display data."""

import re
import unicodedata

from app.domain.catalog import Category
from app.domain.search import (
    FilterConstraint,
    Modality,
    Operator,
    Origin,
    QueryRepresentation,
    SearchOptions,
)


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFD", value.lower().replace("đ", "d"))
    return " ".join(
        re.sub(
            r"[^a-z0-9., ]",
            " ",
            "".join(c for c in value if not unicodedata.combining(c)),
        ).split()
    )


def amount(value: str) -> int | None:
    text = re.sub(r"\s+dong$", "", normalize(value)).strip()
    # Vietnamese "triệu rưỡi" means another half of that explicitly spoken unit.
    # Consume it whole; never truncate a budget at the word before "rưỡi".
    half = re.fullmatch(r"(.+?)\s+(nghin|ngan|trieu|tr|cu|ty|ti)\s+ruoi", text)
    if half:
        whole = amount(half[1])
        scale = {
            "nghin": 1000,
            "ngan": 1000,
            "trieu": 1000000,
            "tr": 1000000,
            "cu": 1000000,
            "ty": 1000000000,
            "ti": 1000000000,
        }[half[2]]
        if whole is not None and 0 <= whole < 1000:
            half_result = whole * scale + scale // 2
            return half_result if half_result <= 10**12 else None
        return None
    if "ruoi" in text.split():
        return None
    number = re.fullmatch(r"(\d+(?:[.,]\d+)*)\s*(k|nghin|ngan|tr|trieu|cu|ty|ti)?", text)
    if number:
        from decimal import Decimal

        multiplier = {
            "k": 1000,
            "nghin": 1000,
            "ngan": 1000,
            "tr": 1000000,
            "trieu": 1000000,
            "cu": 1000000,
            "ty": 1000000000,
            "ti": 1000000000,
        }
        numeric = number[1]
        if re.fullmatch(r"\d{1,3}(?:[.]\d{3})+", numeric):
            numeric = numeric.replace(".", "")
        elif not re.fullmatch(r"\d+(?:[.,]\d+)?", numeric):
            return None
        result = Decimal(numeric.replace(",", ".")) * multiplier.get(number[2], 1)
        return int(result) if result == int(result) and result <= 10**12 else None
    digits = {
        "khong": 0,
        "mot": 1,
        "hai": 2,
        "ba": 3,
        "bon": 4,
        "tu": 4,
        "nam": 5,
        "lam": 5,
        "sau": 6,
        "bay": 7,
        "tam": 8,
        "chin": 9,
    }

    def group(tokens: list[str]) -> int | None:
        if len(tokens) == 1 and tokens[0].isdigit():
            return int(tokens[0])
        subtotal = 0
        if len(tokens) >= 2 and tokens[0] in digits and tokens[1] == "tram":
            subtotal = digits[tokens[0]] * 100
            tokens = tokens[2:]
            if tokens and tokens[0] in {"linh", "le"}:
                tokens = tokens[1:]
                return (
                    subtotal + digits[tokens[0]]
                    if len(tokens) == 1 and tokens[0] in digits
                    else None
                )
        if not tokens:
            return subtotal
        if len(tokens) == 1 and tokens[0] in digits:
            return subtotal + digits[tokens[0]]
        if tokens[0] == "muoi":
            tens, tail = 10, tokens[1:]
        elif (
            len(tokens) >= 2
            and tokens[0] in digits
            and digits[tokens[0]] >= 2
            and tokens[1] == "muoi"
        ):
            tens, tail = digits[tokens[0]] * 10, tokens[2:]
        else:
            return None
        if not tail:
            return subtotal + tens
        return subtotal + tens + digits[tail[0]] if len(tail) == 1 and tail[0] in digits else None

    units = {
        "k": 1000,
        "nghin": 1000,
        "ngan": 1000,
        "tr": 10**6,
        "trieu": 10**6,
        "cu": 10**6,
        "ty": 10**9,
        "ti": 10**9,
    }
    total, previous = 0, 10**13
    pending: list[str] = []
    for token in text.split():
        if token not in units:
            pending.append(token)
            continue
        scale = units[token]
        parsed = group(pending)
        if parsed is None or not pending or scale >= previous or not 0 <= parsed < 1000:
            return None
        total += parsed * scale
        previous, pending = scale, []
    if pending:
        parsed = group(pending)
        if parsed is None or (total and parsed >= previous):
            return None
        total += parsed
    return total if text and 0 <= total <= 10**12 else None


COLORS = {
    "den": "đen",
    "black": "đen",
    "trang": "trắng",
    "white": "trắng",
    "do": "đỏ",
    "red": "đỏ",
    "xanh than": "xanh than",
    "navy": "xanh than",
    "xanh nhat": "xanh nhạt",
    "be": "be",
    "xanh duong": "xanh dương",
    "blue": "xanh dương",
    "xanh la": "xanh lá",
    "green": "xanh lá",
    "xam": "xám",
    "grey": "xám",
    "gray": "xám",
    "nau": "nâu",
    "brown": "nâu",
    "hong": "hồng",
    "pink": "hồng",
    "vang": "vàng",
    "yellow": "vàng",
    "mau tim": "tím",
    "purple": "tím",
}
MATERIALS = {
    "len": "len",
    "wool": "len",
    "cotton": "cotton",
    "da": "da",
    "leather": "da",
}
ALIASES = {
    "ao phong": "ao thun",
    "sneaker": "giay the thao",
    "sneakers": "giay the thao",
    "mens sweater": "ao len nam",
    "men sweater": "ao len nam",
    "sweater nam": "ao len nam",
    "tui deo cheo nu": "tui deo cheo",
    "hoodie": "ao hoodie nam",
    "sweater": "ao len",
}
ORDER_INTENT = re.compile(
    r"\b(?:(?:kiem tra|tra cuu|theo doi|check)\s*(?:don hang|don|order)\b|"
    r"(?:kiem tra|tra cuu|theo doi|check|order|don hang)\s*#?\s*(?:hm[a-f0-9]{14}|\d{6,24})\b)"
)


# Negation scopes are working text only. The original transcript remains raw_text.
_NEGATIVE = re.compile(
    r"\bkhong\s+(?!(?:qua|duoi|tren|re\s+hon|dat\s+hon|day|tham|gi|mui|on|tieng|"
    r"biet|ro|chac|dong|nghin|ngan|trieu|tram|muoi|k)\b)(?!co\s+day\b)\w+"
)
_CLAUSE_END = re.compile(
    r"[,;.!?](?!\d)|\b(?:ma|nhung)\b|"
    r"\b(?:toi|minh|em|anh|chi|ban)\s+(?:muon|can|chon|lay|mua|tim)\b"
)


def _negative_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    for match in _NEGATIVE.finditer(text):
        if any(start <= match.start() < end for start, end in spans):
            continue
        ending = _CLAUSE_END.search(text, match.end())
        end = ending.start() if ending else len(text)
        spans.append((match.start(), end))
    return spans


def _positive_text(text: str) -> str:
    parts, cursor = [], 0
    for start, end in _negative_spans(text):
        parts.append(text[cursor:start])
        cursor = end
    parts.append(text[cursor:])
    return " ".join(" ".join(parts).split())


def _category_present(raw: str, name: str) -> bool:
    canonical: dict[str, set[str]] = {}
    for token in re.findall(r"[^\W_]+", name.lower()):
        canonical.setdefault(normalize(token), set()).add(token)

    def shadow(match: re.Match[str]) -> str:
        word = match[0].lower()
        expected = canonical.get(normalize(word))
        # Unaccented Vietnamese stays supported, but accented bạn/chào/gói/cọc
        # cannot masquerade as bàn/chảo/gối/cốc after tone folding.
        if expected and not word.isascii() and word not in expected:
            if not (word == "giầy" and "giày" in expected):
                return " zzcategoryhomographzz "
        return match[0]

    working = normalize(re.sub(r"[^\W_]+", shadow, raw))
    for alias, target in ALIASES.items():
        working = re.sub(rf"\b{re.escape(alias)}\b", target, working)
    return bool(re.search(rf"\b{re.escape(normalize(name))}\b", _positive_text(working)))


def _mentions(
    text: str, categories: list[Category], brands: tuple[str, ...]
) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    category_spans: list[tuple[int, int, str]] = []
    for category in categories:
        for match in re.finditer(rf"\b{re.escape(normalize(category.name_vi))}\b", text):
            category_spans.append((match.start(), match.end(), category.id))
    occupied: set[int] = set()
    for start, end, identifier in sorted(category_spans, key=lambda row: -(row[1] - row[0])):
        if occupied.intersection(range(start, end)):
            continue
        found.setdefault("danh mục", set()).add(identifier)
        occupied.update(range(start, end))
    attributes = "".join(" " if i in occupied else c for i, c in enumerate(text))
    attributes = re.sub(r"\b(?:toi da|khong qua)\b", " ", attributes)
    for key, mapping in (
        ("màu", COLORS),
        ("chất liệu", MATERIALS),
        ("giới tính", {"nam": "nam", "nu": "nữ", "men": "nam", "women": "nữ"}),
        (
            "thương hiệu",
            {name: name for name in ("samsung", "apple", "adidas", "nike")},
        ),
    ):
        for alias, canonical in mapping.items():
            if re.search(rf"\b{re.escape(alias)}\b", attributes):
                found.setdefault(key, set()).add(canonical)
    return found


def shopping_clarification(
    text: str, categories: list[Category], brands: list[str] | None = None
) -> str | None:
    """Ask instead of silently treating an unsupported exclusion/OR as equality."""
    normalized = normalize(text)
    positive = _positive_text(normalized)
    selected_brands = _public_brands(brands)
    mentions = _mentions(positive, categories, selected_brands)
    if re.search(r"\b(?:hoac|hay|or)\b", positive) and any(
        len(values) > 1 for values in mentions.values()
    ):
        return "Bạn hãy chọn một danh mục hoặc thuộc tính cụ thể để tìm chính xác hơn."
    for start, end in _negative_spans(normalized):
        negative = _mentions(normalized[start:end], categories, selected_brands)
        if not negative or any(
            not (mentions.get(key, set()) - values) for key, values in negative.items()
        ):
            return "Bạn hãy nói một lựa chọn cụ thể thay cho điều kiện loại trừ này."
    rep = RuleQueryParser(categories, brands).parse(text)
    prices = {c.key: c for c in rep.hard_filters if c.key in {"price_min", "price_max"}}
    if "price_min" in prices and "price_max" in prices:
        lower, upper = prices["price_min"], prices["price_max"]
        minimum = int(lower.value) + (1 if lower.operator == "gt" else 0)
        maximum = int(upper.value) - (1 if upper.operator == "lt" else 0)
        if minimum > maximum:
            return "Khoảng giá đang mâu thuẫn. Bạn hãy kiểm tra lại mức thấp nhất và cao nhất."
    return None


def _public_brands(brands: list[str] | None) -> tuple[str, ...]:
    values = ["samsung", "apple", "adidas", "nike"] if brands is None else brands
    return tuple(
        dict.fromkeys(name.strip() for name in values[:512] if name.strip() and len(name) <= 80)
    )


def _brand_aliases(brand: str) -> tuple[str, ...]:
    # A reviewed CamelCase name also accepts natural speech with a word boundary.
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", brand)
    return tuple(dict.fromkeys((normalize(brand), normalize(spaced))))


class RuleQueryParser:
    def __init__(self, categories: list[Category], brands: list[str] | None = None):
        self.categories = categories
        self.brands = _public_brands(brands)

    def clarification(self, text: str) -> str | None:
        return shopping_clarification(text, self.categories, list(self.brands))

    def parse(
        self,
        text: str,
        modality: Modality = "text",
        options: SearchOptions | None = None,
    ) -> QueryRepresentation:
        options = options or SearchOptions()
        raw = unicodedata.normalize("NFC", text)
        normalized = normalize(raw)
        for alias, canonical in ALIASES.items():
            normalized = re.sub(rf"\b{re.escape(alias)}\b", canonical, normalized)
        hard: dict[str, FilterConstraint] = {}
        soft: list[FilterConstraint] = []

        def add(
            key: str,
            value: str | int,
            origin: Origin = "explicit_text",
            op: Operator = "eq",
        ) -> None:
            hard[key] = FilterConstraint(key, value, origin, 1.0, op)

        normalized = _positive_text(normalized)
        matches = [c for c in self.categories if _category_present(raw, c.name_vi)]
        if matches:
            winner = max(matches, key=lambda c: (len(normalize(c.name_vi)), c.level))
            add("category", winner.id)
        elif re.search(r"\bao len\b", normalized):
            add("category", "ao-len-nam|ao-len-nu", "inferred", "any")
        elif re.search(r"\bao\b", normalized):
            add("category", "ao-nam|ao-nu|ao-khoac-nam", "inferred", "any")
        # Category words can be homographs ("búp bê" is not beige), as can
        # price qualifiers ("tối đa" is not leather). Parse attributes outside them.
        # Keep accent-bearing homographs distinct before interpreting bare color aliases.
        # Unaccented "mau do" remains supported; Vietnamese đồ/đó/độ are not red.
        attribute_source = re.sub(
            r"\b(?:đồ|đó|độ|đỗ|đo|bé|đèn|đến|đã|lên|bè|hỏng)\b",
            " ",
            raw,
            flags=re.IGNORECASE,
        )
        attribute_text = re.sub(
            r"\b(?:toi da|khong qua)\b",
            " ",
            _positive_text(normalize(attribute_source)),
        )
        if matches:
            attribute_text = re.sub(
                rf"\b{re.escape(normalize(winner.name_vi))}\b", " ", attribute_text
            )
        for alias, canonical in sorted(COLORS.items(), key=lambda p: -len(p[0])):
            if re.search(rf"\b{re.escape(alias)}\b", attribute_text):
                add("color", canonical)
                break
        for alias, canonical in MATERIALS.items():
            if re.search(rf"\b(?:chat lieu\s+)?{alias}\b", attribute_text) and (
                alias != "len" or "ao len" not in normalized or "chat lieu len" in normalized
            ):
                add("material", canonical)
                break
        gender_text = _positive_text(normalize(re.sub(r"\bnăm\b", " ", raw, flags=re.IGNORECASE)))
        if re.search(
            r"\b(nam|men|male)\b(?!\s+(?:tram|muoi|nghin|ngan|k|doi|cai|chiec|bo)\b)",
            gender_text,
        ):
            add("gender", "nam")
        elif re.search(r"\b(nu|women|female)\b", normalized):
            add("gender", "nữ")
        for brand in sorted(self.brands, key=len, reverse=True):
            if any(
                re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in _brand_aliases(brand)
            ):
                add("brand", brand)
                break
        size = re.search(r"\bsize\s*(xxl|xl|xs|s|m|l)\b", normalized)
        if size:
            add("size", size[1].upper())
        # Consume the whole contiguous number phrase before parsing. A partial match
        # must never turn 1.2 million into 1 million or 550k into 500k.
        number_word = (
            r"(?:khong|mot|hai|ba|bon|tu|nam|lam|sau|bay|tam|chin|muoi|tram|linh|le|"
            r"nghin|ngan|trieu|tr|cu|ty|ti|k|dong|ruoi)"
        )
        money_pattern = (
            rf"((?:\d+(?:[.,]\d+)*\s*(?:nghin|ngan|trieu|tr|cu|ty|ti|k)?|{number_word})"
            rf"(?:\s+{number_word})*)"
        )
        qualifiers = (
            r"(khong duoi|it nhat|toi thieu|khong tren|nhieu nhat|"
            r"khong qua|toi da|khong re hon|khong dat hon|re hon|it hon|thap hon|"
            r"dat hon|cao hon|duoi|under|tren|over|tu|tam|khoang)"
        )
        for match in re.finditer(rf"\b{qualifiers}\s+(?:la\s+)?{money_pattern}\b", normalized):
            value = amount(match[2])
            if value is None:
                continue
            kind = match[1]
            if kind in {"tam", "khoang"}:
                soft.append(FilterConstraint("price_target", value, "explicit_text", 0.8))
            elif kind in {
                "duoi",
                "under",
                "khong qua",
                "toi da",
                "khong tren",
                "nhieu nhat",
                "khong dat hon",
                "re hon",
                "it hon",
                "thap hon",
            }:
                add(
                    "price_max",
                    value,
                    op="lt" if kind in {"duoi", "under", "re hon", "it hon", "thap hon"} else "lte",
                )
            else:
                add(
                    "price_min",
                    value,
                    op="gt" if kind in {"tren", "over", "dat hon", "cao hon"} else "gte",
                )
        for lower, upper in re.findall(
            rf"\btu\s*{money_pattern}\s+(?:den|toi)\s*{money_pattern}\b", normalized
        ):
            minimum, maximum = amount(lower), amount(upper)
            # A single trailing unit applies to both endpoints in this one range.
            # Explicit "đồng" and already scaled/grouped amounts never borrow units.
            if minimum is not None and maximum is not None:
                lower_units = re.search(
                    r"(?:nghin|ngan|trieu|tr|cu|ty|ti|k|dong)(?:\s+dong)?$", lower
                )
                upper_unit = re.search(r"(nghin|ngan|trieu|tr|cu|ty|ti|k)(?:\s+dong)?$", upper)
                if not lower_units and upper_unit and 0 <= minimum < 1000:
                    scaled = amount(f"{minimum}{upper_unit[1]}")
                    if scaled is not None:
                        minimum = scaled
                add("price_min", minimum, op="gte")
                add("price_max", maximum, op="lte")
        for match in re.finditer(rf"\b{money_pattern}\s+tro\s+(xuong|len)\b", normalized):
            value = amount(match[1])
            if value is not None:
                add(
                    "price_max" if match[2] == "xuong" else "price_min",
                    value,
                    op="lte" if match[2] == "xuong" else "gte",
                )
        if re.search(r"\b(mua dong|winter|giu am|am ap)\b", normalized):
            soft.append(FilterConstraint("season", "mùa đông", "explicit_text", 1))
        for style in ["cong so", "du lich", "toi gian", "the thao"]:
            if style in normalized:
                soft.append(FilterConstraint("style", style, "explicit_text", 0.7))
        for key in [
            "category",
            "color",
            "material",
            "brand",
            "gender",
            "price_min",
            "price_max",
        ]:
            value = getattr(options, key)
            if value is not None and value != "":
                add(
                    key,
                    value,
                    "ui_selected",
                    "gte" if key == "price_min" else "lte" if key == "price_max" else "eq",
                )
        return QueryRepresentation(
            modality,
            raw,
            normalized,
            hard_filters=tuple(hard.values()),
            soft_preferences=tuple(soft),
        )
