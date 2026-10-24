"""Build original, deterministic CC0 catalog JSON and SVG illustrations. No network."""

import hashlib
import json
import unicodedata
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1] / "benchmarks" / "fixtures"


def slug(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "-".join("".join(c for c in text if not unicodedata.combining(c)).split())


def build() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "images").mkdir(exist_ok=True)
    taxonomy = {
        "Thời trang nam": {
            "Áo nam": ["Áo len nam", "Áo sơ mi nam", "Áo thun nam"],
            "Quần nam": ["Quần tây nam", "Quần jean nam", "Quần short nam"],
            "Áo khoác nam": ["Áo phao nam", "Áo hoodie nam", "Áo khoác nhẹ nam"],
        },
        "Thời trang nữ": {
            "Áo nữ": ["Áo len nữ", "Áo sơ mi nữ", "Áo thun nữ"],
            "Váy nữ": ["Váy dài", "Váy ngắn", "Chân váy"],
            "Quần nữ": ["Quần tây nữ", "Quần jean nữ", "Quần short nữ"],
        },
        "Giày dép": {
            "Giày": ["Giày thể thao", "Giày tây", "Giày búp bê"],
            "Dép": ["Dép quai ngang", "Sandal", "Dép đi trong nhà"],
        },
        "Phụ kiện": {
            "Túi và balô": ["Túi đeo chéo", "Túi xách", "Balô", "Túi du lịch"],
            "Phụ kiện mặc": ["Mũ", "Khăn quàng", "Thắt lưng"],
            "Phụ kiện khác": ["Ví", "Tất", "Găng tay"],
        },
    }
    categories: list[dict[str, object]] = []
    leaves: list[str] = []
    for top, groups in taxonomy.items():
        categories.append(
            dict(
                id=slug(top),
                slug=slug(top),
                name_vi=top,
                parent_id=None,
                level=0,
                sort_order=len(categories),
            )
        )
        for group, names in groups.items():
            categories.append(
                dict(
                    id=slug(group),
                    slug=slug(group),
                    name_vi=group,
                    parent_id=slug(top),
                    level=1,
                    sort_order=len(categories),
                )
            )
            for name in names:
                categories.append(
                    dict(
                        id=slug(name),
                        slug=slug(name),
                        name_vi=name,
                        parent_id=slug(group),
                        level=2,
                        sort_order=len(categories),
                    )
                )
                leaves.append(name)

    products: list[dict[str, object]] = []

    def add(
        pid: str,
        name: str,
        category: str,
        price: int,
        color: str = "xanh nhạt",
        **extra: object,
    ) -> None:
        products.append(
            dict(
                id=pid,
                slug=f"{slug(name)}-{pid}",
                name_vi=name,
                category_id=slug(category),
                description_vi="Sản phẩm và giá được tạo cho bài thực hành. Dữ liệu mô phỏng.",
                price_vnd=price,
                color=color,
                material="vải mô phỏng",
                size="M",
                gender="nam"
                if "nam" in category
                else "nữ"
                if "nữ" in category
                else None,
                stock=8,
                source_id="hoodoomart-original-fixture",
                publication_status="published",
                verification_status="verified",
                image_license="demo",
                price_kind="demo",
                **extra,
            )
        )

    for i, leaf in enumerate(leaves, 1):
        add(f"catalog-{i:02}", f"{leaf} mẫu thực hành", leaf, 220000 + i * 1000)
    for i, (name, price) in enumerate(
        [
            ("Áo len nam cổ tròn dệt kim", 264000),
            ("Áo len nam cổ lọ", 324000),
            ("Áo len gilê nam", 456000),
            ("Áo len nam vặn thừng", 470000),
            ("Áo len nam dáng rộng", 475000),
            ("Áo len nam cổ tim", 480000),
            ("Áo len nam dệt gân", 485000),
            ("Áo len nam dài tay", 490000),
            ("Áo len nam cổ cao", 495000),
            ("Áo len nam giữ ấm", 499000),
        ],
        1,
    ):
        add(f"sweater-{i:02}", name, "Áo len nam", price, "đen")
        products[-1].update(
            material="len", season="mùa đông", stock=0 if i == 10 else 8
        )
    add("navy-sweater", "Áo len nam xanh than", "Áo len nam", 389000, "xanh than")
    products[-1].update(material="len", season="mùa đông")
    for pid, color, price in [
        ("bag-red", "đỏ", 95000),
        ("bag-navy", "xanh than", 125000),
        ("bag-beige", "be", 145000),
    ]:
        add(pid, f"Túi đeo chéo màu {color}", "Túi đeo chéo", price, color)
    add("order-shirt", "Áo sơ mi tay dài", "Áo sơ mi nam", 115500, "trắng")
    add("order-trousers", "Quần tây nam", "Quần tây nam", 595000, "đen")
    for pid, change in [
        ("hidden-draft", {"publication_status": "draft"}),
        ("hidden-unverified", {"verification_status": "pending"}),
        ("hidden-rights", {"source_id": "quarantined-fixture"}),
        ("hidden-image", {"image_license": "unknown"}),
        ("hidden-history", {"price_kind": "source_historical"}),
    ]:
        add(pid, "Mẫu kiểm thử không xuất bản", "Áo len nam", 100000, "đen")
        products[-1].update(change)

    colors = {
        "đen": "#24313B",
        "xanh than": "#264969",
        "đỏ": "#AD4552",
        "be": "#C7B99E",
        "trắng": "#F0F2F3",
        "xanh nhạt": "#8BB7C9",
    }
    for p in products:
        # Simple original vector art, not a product photograph or image-search quality fixture.
        fill = colors[str(p["color"])]
        title = escape(str(p["name_vi"]))
        if "tui" in str(p["category_id"]):
            shape = '<path d="M155 195 Q250 45 345 195" fill="none" stroke="{0}" stroke-width="18"/><rect x="120" y="175" width="260" height="240" rx="30" fill="{0}"/><path d="M125 250 H375" stroke="#FFFFFF" opacity=".4" stroke-width="5"/>'
        else:
            shape = '<path d="M180 120 L110 145 L45 270 L115 310 L150 250 L150 440 L350 440 L350 250 L385 310 L455 270 L390 145 L320 120 Q250 180 180 120Z" fill="{0}"/><path d="M180 120 Q250 205 320 120 M170 410 H330" fill="none" stroke="#FFFFFF" opacity=".3" stroke-width="8"/>'
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="560" viewBox="0 0 500 560" role="img"><title>{title} — minh họa mô phỏng</title><rect width="500" height="560" fill="#EFF6FA"/>{shape.format(fill)}<ellipse cx="250" cy="480" rx="125" ry="12" fill="#203E59" opacity=".08"/></svg>\n'
        image = ROOT / "images" / f"{p['id']}.svg"
        image.write_text(svg, encoding="utf-8")
        p["image_sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
    payload = dict(
        version="2026-10-21-v1",
        license="CC0-1.0",
        data_profile="demo_seed",
        categories=categories,
        products=products,
        order=dict(
            code="20261005",
            user_id="fixture-customer",
            status="CONFIRMED",
            items=[
                dict(product_id="order-shirt", price_vnd=115500, quantity=1),
                dict(product_id="order-trousers", price_vnd=595000, quantity=1),
            ],
            total_vnd=710500,
        ),
    )
    (ROOT / "catalog.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Generated {len(categories)} categories, {len(products)} original fixture products."
    )


if __name__ == "__main__":
    build()
