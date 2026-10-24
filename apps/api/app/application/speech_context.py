"""Bounded product-context suggestions; the recognizer transcript is never rewritten.

Vocabulary must come from the public catalog, not quarantined import metadata.
These alternatives are proposals for user confirmation, not acoustic evidence.
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import islice

from app.domain.catalog import Product

PRODUCT_CONFUSIONS = {
    "tài nghe": "tai nghe",
    "tay nghe": "tai nghe",
    "dày thể thao": "giày thể thao",
    "giầy thể thao": "giày thể thao",
    "bàng làm việc": "bàn làm việc",
    "áo khoát": "áo khoác",
}
MAX_VOCABULARY = 256
MAX_SUGGESTIONS = 3
MAX_PHRASE_TOKENS = 6
TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
SHOPPING_CUE = re.compile(r"\b(?:mua|tim|chon|san pham|ban co)\b")
ORDER_CUE = re.compile(r"\b(?:don hang|order|hm[a-f0-9]{14})\b")
# A phonetic guess must not change attributes, quantities, price or identifiers.
PROTECTED = frozenset(
    "không một hai ba bốn tư năm lăm sáu bảy tám chín mười trăm nghìn ngàn triệu tỷ "
    "linh lẻ mốt k tr đồng dưới trên từ đến khoảng tối đa thiểu "
    "đen trắng đỏ xanh vàng tím hồng nâu xám bạc cam be nam nữ unisex "
    "da vải len lông cotton gỗ nhựa kim loại".split()
)
# Both are valid, including when only one exists in the current assortment.
VALID_PHRASES = frozenset({"áo lông", "áo len"})
# Reviewed near-sound families cover common Vietnamese regional confusions.
# These still only produce alternatives; accents/region are never inferred.
_NEAR_INITIALS = (("ch", "tr"), ("s", "x"), ("d", "gi"), ("d", "r"), ("gi", "r"), ("l", "n"))
_NEAR_FINALS = (("n", "ng"), ("t", "c"))
_TONES = frozenset({"\u0300", "\u0301", "\u0303", "\u0309", "\u0323"})


@dataclass(frozen=True)
class SpeechVocabularyEntry:
    """An explicit publication/rights assertion supplied by a trusted caller."""

    phrase: str
    source_id: str = ""
    publication_status: str = ""
    verification_status: str = ""
    rights_status: str = ""
    image_rights_status: str = ""


def _clean(text: str) -> str:
    return " ".join(unicodedata.normalize("NFC", text).split())


def public_product_vocabulary(products: Iterable[Product]) -> tuple[SpeechVocabularyEntry, ...]:
    """Build only from CatalogRepository public results, whose image/publication gates ran.

    Product has no publication field: do not use this adapter with draft/import rows.
    Verification, source identity, rights and an approved public image are rechecked.
    Only the category and code-free title prefix are considered; never descriptions.
    """
    entries: list[SpeechVocabularyEntry] = []
    seen: set[str] = set()
    for product in islice(products, 5000):
        if (
            product.verification_status != "verified"
            or product.rights_status not in {"approved", "demo"}
            or not product.source_id
            or not product.image_url
        ):
            continue
        for index, phrase in enumerate(
            (product.category_name, re.split(r"\s[—–]\s", product.name_vi)[0])
        ):
            cleaned = _clean(phrase)
            # A mixed-case title suffix is normally a brand/proper name; do not
            # teach a spelling corrector to rewrite it. Categories still contribute.
            if index == 1 and any(word[0].isupper() for word in cleaned.split()[1:]):
                continue
            phrase = cleaned.lower()
            if phrase in seen or not _phrase_tokens(phrase):
                continue
            seen.add(phrase)
            entries.append(
                SpeechVocabularyEntry(
                    phrase,
                    product.source_id,
                    "published",
                    "verified",
                    product.rights_status,
                    product.rights_status,
                )
            )
            if len(entries) == MAX_VOCABULARY:
                return tuple(entries)
    return tuple(entries)


def _phrase_tokens(phrase: str) -> tuple[str, ...]:
    parts = tuple(TOKEN.findall(phrase))
    if (
        not 2 <= len(parts) <= MAX_PHRASE_TOKENS
        or len(phrase) > 80
        or any(
            not part.isalpha()
            or len(part) > 24
            or any("LATIN" not in unicodedata.name(c, "") for c in part)
            for part in parts
        )
        or " ".join(parts) != phrase
    ):
        return ()
    return parts


def _approved_vocabulary(entries: Iterable[SpeechVocabularyEntry]) -> tuple[tuple[str, ...], ...]:
    accepted: set[tuple[str, ...]] = set()
    for entry in islice(entries, 2048):
        if (
            entry.publication_status != "published"
            or entry.verification_status != "verified"
            or entry.rights_status not in {"approved", "demo"}
            or entry.image_rights_status != entry.rights_status
            or not entry.source_id.strip()
        ):
            continue
        tokens = _phrase_tokens(_clean(entry.phrase).lower())
        if tokens:
            accepted.add(tokens)
        if len(accepted) >= MAX_VOCABULARY:
            break
    # Stable ties do not depend on database row order.
    return tuple(sorted(accepted))


def _without_tone(token: str) -> str:
    return unicodedata.normalize(
        "NFC", "".join(c for c in unicodedata.normalize("NFD", token) if c not in _TONES)
    )


def _one_edit(left: str, right: str) -> bool:
    if abs(len(left) - len(right)) > 1:
        return False
    if len(left) == len(right):
        return sum(a != b for a, b in zip(left, right, strict=True)) == 1
    shorter, longer = (left, right) if len(left) < len(right) else (right, left)
    return any(longer[:i] + longer[i + 1 :] == shorter for i in range(len(longer)))


def _near_syllable(source: str, target: str) -> int | None:
    if source in PROTECTED or target in PROTECTED or not source.isalpha() or not target.isalpha():
        return None
    source_fold, target_fold = _without_tone(source), _without_tone(target)
    if source_fold == target_fold:
        return 0
    for left, right in _NEAR_INITIALS:
        for a, b in ((left, right), (right, left)):
            if source_fold.startswith(a) and target_fold.startswith(b):
                tail = source_fold[len(a) :]
                if len(tail) >= 2 and tail == target_fold[len(b) :]:
                    return 1
    for left, right in _NEAR_FINALS:
        for a, b in ((left, right), (right, left)):
            if source_fold.endswith(a) and target_fold.endswith(b):
                stem = source_fold[: -len(a)]
                if len(stem) >= 2 and stem == target_fold[: -len(b)]:
                    return 1
    # Bounded spelling / near-syllable proposal, not general Vietnamese phonetics.
    if min(len(source_fold), len(target_fold)) >= 3 and _one_edit(source_fold, target_fold):
        return 1
    return None


def product_alternatives(
    text: str, vocabulary: Iterable[SpeechVocabularyEntry] = ()
) -> tuple[str, ...]:
    """Offer at most three opt-in alternatives; preserve all text outside one phrase.

    No vocabulary retains the six legacy reviewed phrase proposals. Catalog-driven
    proposals require a shopping cue, a matching anchor and exactly one near syllable.
    This function never modifies caller text or silently resolves ambiguity.
    """
    from app.application.query_parser import ORDER_INTENT, normalize

    text = unicodedata.normalize("NFC", text)
    if not text.strip() or len(text) > 300:
        return ()
    normalized = normalize(text)
    if ORDER_INTENT.search(normalized) or ORDER_CUE.search(normalized):
        return ()
    shopping = bool(SHOPPING_CUE.search(normalized))
    choices: list[tuple[int, str]] = []
    lower = text.lower()
    for source, target in PRODUCT_CONFUSIONS.items():
        # Bare known error phrases remain compatible; prose needs shopping intent.
        if not shopping and lower.strip() != source:
            continue
        match = re.search(rf"\b{re.escape(source)}\b", text, flags=re.IGNORECASE)
        if match:
            candidate = text[: match.start()] + target + text[match.end() :]
            choices.append((-1, candidate))
    if not shopping:
        return tuple(dict.fromkeys(candidate for _, candidate in choices))[:MAX_SUGGESTIONS]
    phrases = _approved_vocabulary(vocabulary)
    known = set(phrases) | {tuple(phrase.split()) for phrase in VALID_PHRASES}
    matches = list(TOKEN.finditer(text))
    tokens = [match.group().lower() for match in matches]
    # Protect any span which is already a valid catalog phrase; do not reinterpret
    # a genuine product as another assortment item just because their sounds match.
    protected_spans: set[int] = set()
    for start in range(len(tokens)):
        for phrase in known:
            if tuple(tokens[start : start + len(phrase)]) == phrase:
                protected_spans.update(range(start, start + len(phrase)))
    for phrase in phrases:
        for start in range(len(tokens) - len(phrase) + 1):
            window = tokens[start : start + len(phrase)]
            differences = [i for i, (a, b) in enumerate(zip(window, phrase, strict=True)) if a != b]
            if len(differences) != 1:
                continue
            offset = differences[0]
            position = start + offset
            if position in protected_spans:
                continue
            # Never bridge punctuation/identifiers or edit a token embedded in a code.
            span = text[matches[start].start() : matches[start + len(phrase) - 1].end()]
            if not re.fullmatch(r"[^\W_]+(?:\s+[^\W_]+)+", span):
                continue
            source_match = matches[position]
            before, after = text[: source_match.start()], text[source_match.end() :]
            if re.search(r"\w[-_/.:]$", before) or re.match(r"^[-_/.:]\w", after):
                continue
            if source_match.group() != source_match.group().lower():
                continue
            score = _near_syllable(window[offset], phrase[offset])
            anchors = [
                word for i, word in enumerate(phrase) if i != offset and word not in PROTECTED
            ]
            if score is None or not anchors:
                continue
            candidate = text[: source_match.start()] + phrase[offset] + text[source_match.end() :]
            choices.append((score, candidate))
    return tuple(
        dict.fromkeys(candidate for _, candidate in sorted(choices) if len(candidate) <= 300)
    )[:MAX_SUGGESTIONS]
