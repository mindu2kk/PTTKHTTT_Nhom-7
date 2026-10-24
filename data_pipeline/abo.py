"""Bounded, reproducible ABO acquisition. No inference, scraping or invented source offers."""

import argparse
import asyncio
import csv
import gzip
import hashlib
import io
import json
import re
from concurrent.futures import ThreadPoolExecutor
from collections import Counter, defaultdict
from pathlib import Path

import httpx
from PIL import Image, ImageOps

from app.infrastructure.abo_mapping import TYPES

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "data/private/m8"
PUBLIC = ROOT / "data/catalog/images"
BASE = "https://amazon-berkeley-objects.s3.amazonaws.com/"
SOURCE = "amazon-berkeley-objects"
REVISION = "listings_0-49304dd0edc3aa3d4cb19231927732fc"
LICENSE = "CC-BY-4.0"
IMAGE_LIMIT = 5 * 1024 * 1024
GROUPS = {
    "nam": ("thoi-trang-nam", "Thời trang nam", "Giày nam", 490000),
    "nu": ("thoi-trang-nu", "Thời trang nữ", "Giày nữ", 490000),
    "dien-tu": ("dien-tu", "Điện tử", "Phụ kiện điện tử", 190000),
    "gia-dung": ("gia-dung", "Gia dụng", "Đồ gia dụng", 290000),
}
COLORS = {
    "black": "đen",
    "white": "trắng",
    "navy": "xanh than",
    "blue": "xanh dương",
    "red": "đỏ",
    "brown": "nâu",
    "beige": "be",
    "grey": "xám",
    "gray": "xám",
    "pink": "hồng",
    "green": "xanh lá",
    "yellow": "vàng",
    "tan": "nâu nhạt",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def value(row, key):
    values = row.get(key, [])
    return next(
        (str(v["value"]) for v in values if v.get("language_tag", "").startswith("en")),
        "",
    )


def classify(row):
    title = value(row, "item_name")
    if re.search(r"\b(swatch|sample|replacement)\b", title, re.IGNORECASE):
        return None
    kind = row.get("product_type", [{}])[0].get("value")
    if (
        not title
        or not row.get("item_id")
        or not row.get("domain_name")
        or not row.get("main_image_id")
    ):
        return None
    if kind in {"SHOES", "BOOT", "SANDAL"}:
        lower = title.lower()
        gender = (
            "nu"
            if re.search(r"\bwomen(?:'s|s)?\b", lower)
            else "nam"
            if re.search(r"\bmen(?:'s|s)?\b", lower)
            else None
        )
        if gender is None or re.search(r"\b(boy|girl|toddler|kid|child)", lower):
            return None
        label = {"SHOES": "Giày", "BOOT": "Bốt", "SANDAL": "Sandal"}[kind]
        return (
            gender,
            f"giay-{gender}",
            f"{label} {'nữ' if gender == 'nu' else 'nam'}",
            490000,
        )
    return TYPES.get(kind)


def download(client, key, target, limit):
    """Resume a partial S3 object; immutable objects are verified in the manifest."""
    if target.exists():
        if target.stat().st_size > limit:
            raise ValueError("Cached download exceeds bound")
        return target.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".partial")
    offset = partial.stat().st_size if partial.exists() else 0
    with client.stream(
        "GET", BASE + key, headers={"Range": f"bytes={offset}-"} if offset else {}
    ) as response:
        response.raise_for_status()
        resumed = offset and response.status_code == 206
        if resumed and not response.headers.get("content-range", "").startswith(
            f"bytes {offset}-"
        ):
            raise ValueError("Invalid resumed range")
        total = offset if resumed else 0
        with partial.open("ab" if resumed else "wb") as output:
            for chunk in response.iter_bytes(65536):
                total += len(chunk)
                if total > limit:
                    raise ValueError("Download exceeds configured bound")
                output.write(chunk)
    partial.replace(target)
    return target.read_bytes()


def approved_rights():
    review = json.loads(
        (ROOT / "data/sources/abo-rights.json").read_text(encoding="utf8")
    )
    if (
        review.get("status") != "approved"
        or review.get("license") != LICENSE
        or review.get("revision") != REVISION
    ):
        raise ValueError("Source rights or revision not approved")
    return review


def derivatives(raw, stem):
    with Image.open(io.BytesIO(raw)) as source:
        if (
            source.format not in {"JPEG", "PNG", "WEBP"}
            or source.width * source.height > 12_000_000
        ):
            raise ValueError("Unsupported or oversized image")
        source.load()
        image = ImageOps.exif_transpose(source).convert("RGB")
        if min(image.size) < 80:
            raise ValueError("Image too small")
        output = []
        for suffix, size in [("", 960), ("-320", 320)]:
            copy = image.copy()
            copy.thumbnail((size, size), Image.Resampling.LANCZOS)
            stream = io.BytesIO()
            copy.save(stream, format="WEBP", quality=85, method=4)
            content = stream.getvalue()
            path = PUBLIC / f"{stem}{suffix}.webp"
            if not path.exists() or digest(path.read_bytes()) != digest(content):
                path.write_bytes(content)
            if not suffix:
                output = [copy.width, copy.height, digest(content)]
        return output


def acquire(limit=300, reviewed=False):
    review = approved_rights()
    selection = json.loads(
        (ROOT / "data/sources/abo-selection.json").read_text(encoding="utf8")
    )
    approved_ids = set(selection["external_ids"]) if reviewed else None
    if reviewed:
        if selection["revision"] != REVISION:
            raise ValueError("Reviewed selection revision mismatch")
        limit = len(approved_ids)
    qc = json.loads(
        (ROOT / "data/sources/abo-image-qc.json").read_text(encoding="utf8")
    )
    rejected_photos = {row["source_image_id"] for row in qc["rejected"]}
    if not 1 <= limit <= 1000:
        raise ValueError("Explicit bounded sample: 1..1000")
    STAGE.mkdir(parents=True, exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=45, follow_redirects=False) as client:
        listing = download(
            client,
            "listings/metadata/listings_0.json.gz",
            STAGE / "listings_0.json.gz",
            6_000_000,
        )
        if hashlib.md5(listing).hexdigest() != "49304dd0edc3aa3d4cb19231927732fc":
            raise ValueError("Listing revision changed")
        metadata = download(
            client, "images/metadata/images.csv.gz", STAGE / "images.csv.gz", 8_000_000
        )
        if (
            digest(listing) != review["listing_sha256"]
            or digest(metadata) != review["image_metadata_sha256"]
        ):
            raise ValueError("Reviewed metadata digest changed; stop for source review")
        image_map = {
            r["image_id"]: r
            for r in csv.DictReader(io.StringIO(gzip.decompress(metadata).decode()))
        }
        candidates = defaultdict(list)
        type_counts = Counter()
        seen_ids, seen_images = set(), set()
        for line in gzip.decompress(listing).decode().splitlines():
            row = json.loads(line)
            mapping = classify(row)
            if mapping is None:
                continue
            group, leaf, label, price = mapping
            external = f"{row['domain_name']}:{row['item_id']}"
            if approved_ids is not None and external not in approved_ids:
                continue
            image_id = row["main_image_id"]
            if (
                external in seen_ids
                or image_id in seen_images
                or image_id not in image_map
                or image_id in rejected_photos
            ):
                continue
            # Category-balanced selection, not 300 near-identical phone cases.
            quota = (group, label)
            if type_counts[quota] >= (100 if group in {"nam", "nu"} else 30):
                continue
            seen_ids.add(external)
            seen_images.add(image_id)
            type_counts[quota] += 1
            candidates[group].append((row, leaf, label, price, external))
        selected = []
        while len(selected) < limit and any(candidates.values()):
            for group in GROUPS:
                if candidates[group] and len(selected) < limit:
                    selected.append((group, *candidates[group].pop(0)))
        report = {
            "source": SOURCE,
            "revision": REVISION,
            "license": LICENSE,
            "metadata_sha256": digest(metadata),
            "listing_sha256": digest(listing),
            "rows_scanned": 9232,
            "records": [],
            "errors": [],
        }
        pending = {}
        for _, row, *_ in selected:
            for image_id in [row["main_image_id"], *row.get("other_image_id", [])[:1]]:
                info = image_map.get(image_id)
                if info and re.fullmatch(
                    r"[0-9a-f]{2}/[0-9a-f]+\.(jpg|png)", info["path"]
                ):
                    pending[info["path"]] = info["path"]

        def prefetch(path):
            try:
                download(
                    client,
                    "images/original/" + path,
                    STAGE / "originals" / path,
                    IMAGE_LIMIT,
                )
            except (ValueError, httpx.HTTPError, OSError):
                pass  # Per-record validation below records errors and excludes invalid items.

        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(prefetch, pending))
        used_hashes = set()
        for group, row, leaf, label, price, external in selected:
            pid = "abo-" + digest(external.encode())[:20]
            photos = []
            try:
                for n, image_id in enumerate(
                    [row["main_image_id"], *row.get("other_image_id", [])[:1]]
                ):
                    info = image_map.get(image_id)
                    if not info or not re.fullmatch(
                        r"[0-9a-f]{2}/[0-9a-f]+\.(jpg|png)", info["path"]
                    ):
                        if n == 0:
                            raise ValueError("Missing or unsafe source image mapping")
                        continue
                    raw = download(
                        client,
                        "images/original/" + info["path"],
                        STAGE / "originals" / info["path"],
                        IMAGE_LIMIT,
                    )
                    sha = digest(raw)
                    if n == 0 and sha in used_hashes:
                        raise ValueError("Duplicate primary photograph")
                    width, height, public_hash = derivatives(raw, f"{pid}-{n}")
                    photos.append(
                        {
                            "source_image_id": image_id,
                            "source_path": info["path"],
                            "source_sha256": sha,
                            "sha256": public_hash,
                            "url": f"/media/catalog/{pid}-{n}.webp",
                            "width": width,
                            "height": height,
                            "primary": n == 0,
                        }
                    )
                    if n == 0:
                        used_hashes.add(sha)
            except (ValueError, httpx.HTTPError, OSError) as error:
                report["errors"].append(
                    {"external_id": external, "error": str(error)[:220]}
                )
                if not photos or not photos[0]["primary"]:
                    continue
            color_original = value(row, "color")
            color = next(
                (
                    vi
                    for en, vi in COLORS.items()
                    if re.search(rf"\b{en}\b", color_original.lower())
                ),
                color_original[:40] or "Chưa có thông tin",
            )
            brand = value(row, "brand")[:80] or None
            model = value(row, "model_name") or next(
                (str(x["value"]) for x in row.get("model_number", [])), row["item_id"]
            )
            name = f"{label} {brand or ''} — {model}"[:250]
            record = {
                "id": pid,
                "external_id": external,
                "raw": row,
                "group": group,
                "category_id": "abo-" + leaf,
                "category_name": label,
                "name_vi": name,
                "original_name": value(row, "item_name"),
                "description_vi": f"{label} trong bộ dữ liệu Amazon Berkeley Objects. Ảnh chụp và tên gốc liên kết theo mã {row['item_id']}. Màu theo nguồn: {color}. Giá và hạn mức đặt thử của HoodooMart được mô phỏng riêng; không phải chào bán hay tồn kho Amazon.",
                "brand": brand,
                "gender": "nam" if group == "nam" else "nữ" if group == "nu" else None,
                "color": color,
                "material": value(row, "material")[:100],
                "price_vnd": price,
                "demo_capacity": 5,
                "images": photos,
            }
            report["records"].append(record)
            print(f"Validated {len(report['records'])}/{limit}: {pid}", flush=True)
        report["category_distribution"] = dict(
            Counter(r["category_name"] for r in report["records"])
        )
        report["groups"] = dict(Counter(r["group"] for r in report["records"]))
        target = STAGE / "validated.json"
        target.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8"
        )
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["acquire", "dry-run", "import"])
    parser.add_argument("--limit", type=int, default=300)
    parser.add_argument(
        "--reviewed",
        action="store_true",
        help="Reacquire the exact committed, reviewed source-ID subset",
    )
    args = parser.parse_args()
    if args.action == "acquire":
        report = acquire(args.limit, args.reviewed)
        print(
            json.dumps(
                {k: v for k, v in report.items() if k != "records"},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        from app.infrastructure.real_catalog import import_catalog

        print(
            json.dumps(
                asyncio.run(import_catalog(args.action == "dry-run")),
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
