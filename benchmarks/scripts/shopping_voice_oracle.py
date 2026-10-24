"""Freeze100 independently authored shopping TEXT cases from reviewed ABO metadata.

No production parser/ranking imports, inference, DB reads/writes or downloads.
Live public visibility/field equality must be verified before an API score.
"""

import argparse
import hashlib
import json
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "benchmarks/fixtures/shopping_intent_cases.json"
SOURCE = ROOT / "data/private/m8/validated.json"


def norm(value):
    return " ".join(unicodedata.normalize("NFC", str(value)).casefold().split())


def spec(query, category, color=None, price_min=None, price_max=None, brand=None):
    slots = [{"key": "category", "value": f"abo-{category}", "operator": "eq"}]
    if category in {"giay-nam", "giay-nu"}:
        slots.append(
            {
                "key": "gender",
                "value": "nam" if category == "giay-nam" else "nữ",
                "operator": "eq",
            }
        )
    if color:
        slots.append({"key": "color", "value": color, "operator": "eq"})
    if brand:
        slots.append({"key": "brand", "value": brand, "operator": "eq"})
    for key, bound in [("price_min", price_min), ("price_max", price_max)]:
        if bound:
            slots.append({"key": key, "value": bound[1], "operator": bound[0]})
    return {"query": query, "expected_intent": "products", "slots": slots}


# Explicit authored queries/labels. Budgets/relations are hand-specified VND,
# not extracted by the application's parser or inferred from API results.
SPECS = [
    spec("Tôi muốn mua tai nghe", "tai-nghe"),
    spec(
        "Tìm cho tôi tai nghe dưới năm trăm nghìn", "tai-nghe", price_max=("lt", 500000)
    ),
    spec(
        "Có tai nghe nào tối đa bốn trăm nghìn không",
        "tai-nghe",
        price_max=("lte", 400000),
    ),
    spec("Cho tôi xem tai nghe màu đen", "tai-nghe", color="đen"),
    spec(
        "Tôi tìm tai nghe đỏ dưới bốn trăm nghìn",
        "tai-nghe",
        color="đỏ",
        price_max=("lt", 400000),
    ),
    spec("Tai nghe màu xanh lá có không bạn", "tai-nghe", color="xanh lá"),
    spec("Mình cần một tai nghe hồng", "tai-nghe", color="hồng"),
    spec(
        "Tai nghe giá từ ba trăm nghìn đến bốn trăm nghìn",
        "tai-nghe",
        price_min=("gte", 300000),
        price_max=("lte", 400000),
    ),
    spec(
        "Tôi xem tai nghe không dưới ba trăm nghìn",
        "tai-nghe",
        price_min=("gte", 300000),
    ),
    spec("Tìm tai nghe AmazonBasics cho tôi", "tai-nghe", brand="AmazonBasics"),
    spec("Tìm loa dưới sáu trăm nghìn", "loa", price_max=("lt", 600000)),
    spec("Tôi muốn mua loa màu đen", "loa", color="đen"),
    spec("Có loa nào không quá sáu trăm nghìn", "loa", price_max=("lte", 600000)),
    spec("Cho xem loa trên năm trăm nghìn", "loa", price_min=("gt", 500000)),
    spec("Tôi cần loa AmazonBasics", "loa", brand="AmazonBasics"),
    spec("Mình muốn tìm bàn phím", "ban-phim"),
    spec("Bàn phím màu đen nhé", "ban-phim", color="đen"),
    spec("Cho tôi bàn phím dưới ba trăm nghìn", "ban-phim", price_max=("lt", 300000)),
    spec(
        "Bàn phím từ hai trăm nghìn đến ba trăm nghìn",
        "ban-phim",
        price_min=("gte", 200000),
        price_max=("lte", 300000),
    ),
    spec("Tìm bàn phím AmazonBasics", "ban-phim", brand="AmazonBasics"),
    spec("Tôi cần bộ sạc dưới hai trăm nghìn", "bo-sac", price_max=("lt", 200000)),
    spec("Cho xem bộ sạc màu đen", "bo-sac", color="đen"),
    spec("Mình tìm bộ sạc trắng", "bo-sac", color="trắng"),
    spec("Bộ sạc không dưới một trăm nghìn", "bo-sac", price_min=("gte", 100000)),
    spec(
        "Bộ sạc từ một trăm nghìn đến hai trăm nghìn",
        "bo-sac",
        price_min=("gte", 100000),
        price_max=("lte", 200000),
    ),
    spec("Tôi muốn mua chuột máy tính", "chuot"),
    spec("Tìm chuột máy tính dưới hai trăm nghìn", "chuot", price_max=("lt", 200000)),
    spec("Cho xem phụ kiện máy tính màu đen", "phu-kien-may-tinh", color="đen"),
    spec(
        "Tôi cần ốp điện thoại dưới một trăm nghìn",
        "op-dien-thoai",
        price_max=("lt", 100000),
    ),
    spec(
        "Ốp điện thoại không quá một trăm năm mươi nghìn",
        "op-dien-thoai",
        price_max=("lte", 150000),
    ),
    spec("Tôi tìm giày nam", "giay-nam"),
    spec("Cho tôi giày nam màu đen", "giay-nam", color="đen"),
    spec("Giày nam màu nâu có không", "giay-nam", color="nâu"),
    spec("Mình cần giày nam trắng", "giay-nam", color="trắng"),
    spec("Tôi muốn giày nam màu đỏ", "giay-nam", color="đỏ"),
    spec("Cho xem giày nam xanh than", "giay-nam", color="xanh than"),
    spec("Tìm giày nam dưới năm trăm nghìn", "giay-nam", price_max=("lt", 500000)),
    spec(
        "Giày nam từ bốn trăm nghìn đến năm trăm nghìn",
        "giay-nam",
        price_min=("gte", 400000),
        price_max=("lte", 500000),
    ),
    spec(
        "Mình cần giày nam không trên năm trăm nghìn",
        "giay-nam",
        price_max=("lte", 500000),
    ),
    spec(
        "Tìm giày nam Stanton dưới sáu trăm nghìn",
        "giay-nam",
        price_max=("lt", 600000),
        brand="Stanton",
    ),
    spec("Tôi muốn mua giày nữ", "giay-nu"),
    spec("Cho xem giày nữ đen", "giay-nu", color="đen"),
    spec("Tôi cần giày nữ màu nâu", "giay-nu", color="nâu"),
    spec("Tìm giày nữ trắng giúp mình", "giay-nu", color="trắng"),
    spec("Giày nữ hồng có mẫu nào", "giay-nu", color="hồng"),
    spec("Mình tìm giày nữ xanh lá", "giay-nu", color="xanh lá"),
    spec("Cho xem giày nữ dưới năm trăm nghìn", "giay-nu", price_max=("lt", 500000)),
    spec(
        "Giày nữ từ bốn trăm nghìn đến năm trăm nghìn",
        "giay-nu",
        price_min=("gte", 400000),
        price_max=("lte", 500000),
    ),
    spec(
        "Tôi muốn giày nữ không quá năm trăm nghìn",
        "giay-nu",
        price_max=("lte", 500000),
    ),
    spec("Tìm giày nữ Amazon Essentials", "giay-nu", brand="Amazon Essentials"),
    spec("Tôi muốn mua ghế", "ghe"),
    spec("Tìm cho tôi ghế dưới một triệu", "ghe", price_max=("lt", 1000000)),
    spec("Cho xem ghế màu xanh dương", "ghe", color="xanh dương"),
    spec("Mình cần ghế nâu", "ghe", color="nâu"),
    spec("Tìm ghế Rivet", "ghe", brand="Rivet"),
    spec("Tôi muốn bàn dưới một triệu rưỡi", "ban", price_max=("lt", 1500000)),
    spec("Cho tôi xem bàn trắng", "ban", color="trắng"),
    spec("Mình tìm bàn màu xám", "ban", color="xám"),
    spec("Bàn màu nâu có không", "ban", color="nâu"),
    spec("Cho xem bàn Rivet", "ban", brand="Rivet"),
    spec("Tìm ghế sofa dưới ba triệu", "sofa", price_max=("lt", 3000000)),
    spec("Tôi muốn ghế sofa màu xám", "sofa", color="xám"),
    spec("Cho xem ghế sofa xanh than", "sofa", color="xanh than"),
    spec("Mình cần ghế sofa nâu", "sofa", color="nâu"),
    spec(
        "Ghế sofa không quá ba triệu năm trăm nghìn", "sofa", price_max=("lte", 3500000)
    ),
    spec("Tôi cần thảm", "tham"),
    spec("Tìm thảm màu xám", "tham", color="xám"),
    spec(
        "Cho tôi thảm màu be dưới bốn trăm nghìn",
        "tham",
        color="be",
        price_max=("lt", 400000),
    ),
    spec("Mình muốn thảm xanh dương", "tham", color="xanh dương"),
    spec("Cho xem thảm xanh lá", "tham", color="xanh lá"),
    spec("Tôi muốn mua đèn bàn", "den-ban"),
    spec("Tìm đèn bàn dưới năm trăm nghìn", "den-ban", price_max=("lt", 500000)),
    spec("Cho xem đèn bàn trắng", "den-ban", color="trắng"),
    spec("Mình tìm đèn bàn màu hồng", "den-ban", color="hồng"),
    spec("Tôi cần đèn bàn Stone & Beam", "den-ban", brand="Stone & Beam"),
    spec("Tôi cần mua gối", "goi"),
    spec("Cho xem gối dưới hai trăm nghìn", "goi", price_max=("lt", 200000)),
    spec("Mình muốn gối màu đỏ", "goi", color="đỏ"),
    spec("Tìm gối xanh dương", "goi", color="xanh dương"),
    spec(
        "Gối từ một trăm nghìn đến hai trăm nghìn",
        "goi",
        price_min=("gte", 100000),
        price_max=("lte", 200000),
    ),
    spec("Tôi muốn mua cốc", "coc"),
    spec("Cho xem cốc xanh dương", "coc", color="xanh dương"),
    spec("Tìm cốc dưới một trăm nghìn", "coc", price_max=("lt", 100000)),
    spec("Tôi cần cốc AmazonBasics", "coc", brand="AmazonBasics"),
    spec(
        "Cốc từ năm mươi nghìn đến một trăm nghìn",
        "coc",
        price_min=("gte", 50000),
        price_max=("lte", 100000),
    ),
    spec("Tôi muốn mua chảo", "chao"),
    spec("Tìm chảo màu đen", "chao", color="đen"),
    spec("Cho xem chảo dưới bốn trăm nghìn", "chao", price_max=("lt", 400000)),
    spec("Mình cần chảo không trên bốn trăm nghìn", "chao", price_max=("lte", 400000)),
    spec(
        "Chảo từ ba trăm nghìn đến bốn trăm nghìn",
        "chao",
        price_min=("gte", 300000),
        price_max=("lte", 400000),
    ),
    spec("Tôi cần dụng cụ nhà bếp", "dung-cu-bep"),
    spec("Cho xem dụng cụ nhà bếp màu trắng", "dung-cu-bep", color="trắng"),
    spec(
        "Tìm dụng cụ nhà bếp dưới ba trăm nghìn",
        "dung-cu-bep",
        price_max=("lt", 300000),
    ),
    spec(
        "Dụng cụ nhà bếp không dưới hai trăm nghìn",
        "dung-cu-bep",
        price_min=("gte", 200000),
    ),
    spec("Tôi muốn dụng cụ nhà bếp UMI", "dung-cu-bep", brand="UMI"),
    spec("Tôi cần máy pha cà phê", "may-pha-ca-phe"),
    spec("Cho xem máy pha cà phê màu đen", "may-pha-ca-phe", color="đen"),
    spec(
        "Tìm máy pha cà phê dưới một triệu", "may-pha-ca-phe", price_max=("lt", 1000000)
    ),
    spec(
        "Máy pha cà phê từ chín trăm nghìn đến một triệu",
        "may-pha-ca-phe",
        price_min=("gte", 900000),
        price_max=("lte", 1000000),
    ),
    spec(
        "Tôi muốn máy pha cà phê Amazon Brand - Solimo",
        "may-pha-ca-phe",
        brand="Amazon Brand - Solimo",
    ),
]


def matches(product, slots):
    for slot in slots:
        key, value, operator = slot["key"], slot["value"], slot["operator"]
        actual = (
            product["price_vnd"]
            if key.startswith("price_")
            else product["category_id" if key == "category" else key]
        )
        if operator == "eq":
            if norm(actual) != norm(value):
                return False
        elif not {
            "lt": actual < value,
            "lte": actual <= value,
            "gt": actual > value,
            "gte": actual >= value,
        }[operator]:
            return False
    return True


def freeze():
    if FIXTURE.exists():
        raise RuntimeError("Oracle already frozen; never change labels after baseline")
    source = json.loads(SOURCE.read_text("utf8"))
    fields = [
        "id",
        "name_vi",
        "category_id",
        "category_name",
        "price_vnd",
        "color",
        "gender",
        "brand",
    ]
    products = [{key: row.get(key) for key in fields} for row in source["records"]]
    assert len(SPECS) == 100
    cases = []
    for index, definition in enumerate(SPECS, 1):
        ids = sorted(p["id"] for p in products if matches(p, definition["slots"]))
        if not ids:
            raise RuntimeError(
                f"No reviewed catalog product matches authored case{index}"
            )
        cases.append(
            {
                "id": f"SV{index:03d}",
                **definition,
                "ui_filters": {},
                "acceptable_product_ids": ids,
                "audio": None,
                "source_kind": "authored_text",
                "annotation_status": "author_specified_from_reviewed_metadata_not_parser_output",
            }
        )
    fixture = {
        "version": 1,
        "frozen_at": datetime.now(UTC).isoformat(),
        "case_count": 100,
        "scope": "Original manually authored positive shopping TEXT oracle. Not100 people, not audio, not independent human relevance ratings. Product ID sets derive only from hand-labelled category/color/brand/gender/money constraints on reviewed metadata, never parser/API ranking.",
        "catalog_source": {
            "path": SOURCE.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
            "source_id": source["source"],
            "license": source["license"],
            "live_public_verification_required": True,
            "price_scope": "integer VND, demo prices; not Amazon market offers",
        },
        "catalog_snapshot": products,
        "cases": cases,
        "gate": {
            "target_semantic_product_success_rate": 0.7,
            "top_k": 5,
            "hard_constraint_violations_allowed": 0,
            "real_audio_status": "pending_no_domain_audio",
            "allow_text_score_to_pass_real_voice_gate": False,
        },
    }
    FIXTURE.write_text(
        json.dumps(fixture, ensure_ascii=False, indent=2) + "\n", encoding="utf8"
    )
    print(
        json.dumps(
            {
                "cases": len(cases),
                "sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
                "status": "text_oracle_frozen_real_voice_pending",
            }
        )
    )


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    freeze()
