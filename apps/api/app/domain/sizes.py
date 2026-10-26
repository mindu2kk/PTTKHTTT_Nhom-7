import re

SIZES = ("S", "M", "L", "XL", "XXL", "F")


def product_sizes(value: str) -> list[str]:
    """Keep declared clothing sizes; legacy/unsized products use F."""
    tokens = set(re.split(r"[\s,;/|]+", value.upper()))
    tokens = {"XXL" if token == "2XL" else token for token in tokens}
    return [size for size in SIZES if size in tokens] or ["F"]
