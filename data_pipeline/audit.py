"""Offline audit of the original fixture; no external source acquisition."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree


def audit(root: Path) -> dict[str, object]:
    fixture = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    errors: list[str] = []
    categories = {c["id"]: c for c in fixture["categories"]}
    ids: set[str] = set()
    image_bytes = 0
    for p in fixture["products"]:
        if p["id"] in ids:
            errors.append(f"Duplicate ID: {p['id']}")
        ids.add(p["id"])
        if (
            p["category_id"] not in categories
            or not p["name_vi"]
            or p["price_vnd"] <= 0
        ):
            errors.append(f"Invalid required fields: {p['id']}")
        image = root / "images" / f"{p['id']}.svg"
        if not image.is_file():
            errors.append(f"Missing image: {p['id']}")
            continue
        raw = image.read_bytes()
        image_bytes += len(raw)
        if hashlib.sha256(raw).hexdigest() != p["image_sha256"]:
            errors.append(f"Image digest mismatch: {p['id']}")
        try:
            svg = ElementTree.fromstring(raw)
            if svg.tag != "{http://www.w3.org/2000/svg}svg":
                errors.append(f"Invalid SVG: {p['id']}")
        except ElementTree.ParseError:
            errors.append(f"Invalid XML: {p['id']}")
    public = [
        p
        for p in fixture["products"]
        if p["publication_status"] == "published"
        and p["verification_status"] == "verified"
        and p["image_license"] == "demo"
        and p["source_id"] == "hoodoomart-original-fixture"
        and p["price_kind"] == "demo"
    ]
    return dict(
        fixture_version=fixture["version"],
        license=fixture["license"],
        products=len(ids),
        categories_by_level=dict(Counter(c["level"] for c in categories.values())),
        accepted=len(public),
        quarantined_or_unpublished=len(ids) - len(public),
        category_distribution=dict(Counter(p["category_id"] for p in public)),
        missing_required_fields=len(errors),
        image_bytes=image_bytes,
        scope="Original synthetic fixture only; no external rights verification or photograph QA",
        errors=errors,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(Path(__file__).resolve().parents[1] / "benchmarks" / "fixtures")
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    raise SystemExit(1 if result["errors"] else 0)
