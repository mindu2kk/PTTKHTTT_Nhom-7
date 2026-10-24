"""Produce M8 handoff from saved evidence; never rewrite historical M7 acceptance reports."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs/evidence/m8"


def read(name):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8-sig"))


def put(name, value):
    (ROOT / "docs" / name).write_text(value.strip() + "\n", encoding="utf8")


def main():
    audit = read("dataset-audit.json")
    browser = read("browser.json")
    image = read("image-http.json")
    text = read("text-http.json")
    cold = read("image-cold.json")
    index = read("index.json")
    replay = read("index-replay.json")
    imported = read("import-full.json")
    storage = read("storage.json")
    resources = read("resources.json")
    structured = read("structured-data.json")
    log = (EVIDENCE / "after-pytest.txt").read_text(encoding="utf8")
    tests = re.search(r"(\d+) passed in ([\d.]+)s", log)
    assert tests and browser["result"] == "passed" and structured["result"] == "passed"
    distribution = "\n".join(
        f"| {name} | {count} |"
        for name, count in audit["category_distribution"].items()
    )
    put(
        "M8_DATASET_AUDIT.md",
        f"""
# M8 — kiểm toán dữ liệu

Nguồn/revision/license: xem M8_DATASET_SOURCES. Report gốc: `evidence/m8/dataset-audit.json`, import logs và ảnh QC cùng thư mục.

| Hạng mục | Số thực tế |
|---|---:|
| Record real_demo lưu trong DB, gồm nháp QC | {audit["stored_real_records"]} |
| Public/verified ảnh thật | {audit["published_products"]} |
| Ảnh gallery liên kết public | {audit["photos"]} |
| Ảnh mở/đúng hash | {audit["working_photos"]} |
| Vector đúng model/revision/hash | {audit["indexed_photos"]} |
| Thiếu brand | {audit["missing_brand"]} |
| Thiếu màu | {audit["missing_color"]} |
| Thiếu chất liệu | {audit["missing_material"]} |
| Giá nguồn VND merchant-verified | 0 |
| Tồn kho merchant-verified | 0 |

Category levels public: `{audit["categories_by_level"]}`. Giữ cây cũ riêng; thêm nhánh thực tế khi cần, không nhận đây là 4/11/34 đầy đủ của slide.

| Danh mục | Sản phẩm |
|---|---:|
{distribution}

Import mở rộng tạo {imported["created"]}, tái sử dụng {imported["reused"]}; replay cuối không tạo trùng. Pilot12 có1 swatch chuyển nháp/pending sau nhìn ảnh, không xóa raw/ảnh/đơn cũ. Gate từ chối loại này đã được thêm trước nhập mở rộng. Sau đó final QC320 primary phát hiện thêm2 logo/placeholder, đã chuyển nháp/quarantine và thêm denylist để không nhập lại. Catalog cuối lấy số thực tế trong bảng trên, không làm tròn thành320. Fixtures M7 không vào profile real_demo.

Một primary trên mỗi sản phẩm, tối đa một ảnh phụ được chọn khi hợp lệ; thiếu ảnh phụ không phải thiếu ảnh chính. Thumbnail320 cho mỗi ảnh; tổng derivative main WebP public khoảng {audit["photo_bytes"] / 1024 / 1024:.2f} MiB, chưa gồm thumbnail/raw/private. Nội dung ảnh nguồn có thể gồm bố cục catalog, nền trắng, chữ chú thích; không gọi đây là bộ ảnh smartphone tự chụp.

Tên Việt từ mapping loại/brand/model, tên gốc giữ ở detail và raw. Màu ánh xạ khi có bằng chứng, vật liệu nguồn có thể vẫn nguyên ngôn ngữ. Không bịa thuộc tính thiếu, review/sales/stock. Offer và hạn mức đặt thử nằm tách metadata thật, nhãn rõ. Mục tiêu pilot300–500 đạt sau loại2 placeholder; chưa mở rộng/đo catalog thật1000/3000.
""",
    )
    speed = "\n".join(
        f"| {g['concurrency']} | {g['requests']} | {g['service']['p95_ms']} | {g['tcp']['p50_ms']} | {g['tcp']['p95_ms']} | {g['grid_tcp']['p95_ms']} |"
        for g in text["groups"]
    )
    lab = "\n".join(
        f"| {m['width']} | {m['lcp']:.1f} | {m['cls']:.5f} | {m['inp_candidate_ms']} |"
        for m in browser["measurements"]
    )
    memory = "\n".join(
        f"| {c['Name']} | {c['MemUsage']} | {c['CPUPerc']} |"
        for c in resources["containers"]
    )
    put(
        "M8_TEST_REPORT.md",
        f"""
# M8 — kiểm thử và số đo mới

Ngày 2026-10-22, cùng máy Windows/Core i3/RAM như `evidence/hardware.json`; Docker PostgreSQL/API/worker CPU, OpenCLIP revision giữ nguyên. Không dùng số M7 làm kết quả M8. File thay đổi: M8_CHANGED_FILES.md; ảnh đối chiếu trước/sau và qrels giữ trong evidence/m8.

## Lệnh và kết quả

- Baseline trước sửa: `scripts/verify.ps1` — 127 passed/49.43s (`evidence/m8/baseline.txt`).
- Sau sửa: `.venv\\Scripts\\python.exe -m pytest apps/api/tests -q --junitxml=docs/evidence/m8/pytest.xml` — **{tests[1]} passed/{tests[2]}s**. Gồm parser/rights/upload/order/CSRF/IDOR/stock race cũ và import/license/ID/mapping/ảnh hỏng/replay/revision/multiple-gallery/revoked-photo mới.
- Ruff/format (95 tệp), strict mypy37 source files, frontend ESLint/TypeScript, Alembic check và Docker build: log riêng cùng thư mục hoặc `artifacts/m8-web-final-build.log`; không dùng việc tạo file log thay cho exit0.
- Import/dry-run/replay/index/replay: `data_pipeline/abo.py` và `scripts/index_real_images.py`; {index["approved_images"]} ảnh trước final QC, encode/update {index["encoded"]}, skip {index["skipped_unchanged"]}; lần index lặp sau final QC encode{replay["encoded"]}/skip{replay["skipped_unchanged"]}.
- `benchmarks/scripts/m8_browser.py`: {len(browser["results"])} nhóm kết quả đạt — năm viewport, gallery/zoom, cart qty/remove/buy-now, đăng ký/checkout/owner/cancel nhả kho, voice correction, image thật/invalid/empty/404. Voice là câu sửa được nhập, **không phải TC2 ASR**. Không mock catalog/checkout. Thêm actual BFF ASR trên1 VIVOS human clip và corrupt image/audio422, invalid cart cookie422, no-JS cart303 trong media-checks.json; không dùng clip đó làm TC2.
- `m8_evaluate.py prepare/audit/cold/measure`: hash/ảnh/index SQL thật, EXPLAIN thật, HTTP TCP thật. Qrels text là oracle cấu trúc category từ source, không human semantic judgments.
- Sau build cuối, `benchmarks/scripts/m8_structured_data.py` đạt trên Chrome thật: Product JSON-LD không có merchant Offer/InStock cho real_demo, giá đặt thử gắn PropertyValue đúng API, nút/số lượng còn dùng được và sản phẩm thiếu trả404. Bằng chứng `structured-data.json`.

## HTTP trên {audit["published_products"]} sản phẩm public

| Đồng thời | Search requests | Service p95 ms | TCP p50 ms | TCP p95 ms | Grid TCP p95 ms |
|---:|---:|---:|---:|---:|---:|
{speed}

Mỗi nhóm có thêm60 grid requests. Hard category leaks: {[g["category_leaks"] for g in text["groups"]]}. Precision@10/Recall@10/NDCG@10 và kết quả từng câu trong `text-http.json`; category ít hơn10 relevant items có trần Precision@10 thấp, không đổi mẫu số để làm đẹp. Không có benchmark real1000/3000 trong M8.

## Ảnh

Process-cold sau restart worker riêng, API cache hit=false, cache OS không được xóa: HTTP{cold["status"]}, {cold["http_ms"]}ms. Warm full HTTP: **p50={image["warm_http"]["p50_ms"]}ms, p95={image["warm_http"]["p95_ms"]}ms**, {image["queries_measured"]} ảnh query nguồn khác ID/bytes, không nằm trong gallery; warmup riêng không đưa vào số đo. Mọi measured query cached=false.

Recall@1/5/10: {image["recall"]}; NDCG@10={image["ndcg_at_10"]:.4f}. Nhãn relevance là cùng source product ID, chưa có người dùng chấm. Đã nhìn contact sheet, loại explanatory line drawings khỏi bộ query. Ảnh góc khác/detail/lifestyle và phụ kiện; không kết luận điện thoại thực tế/occlusion/cross-brand đã được đánh giá đầy đủ. Failure IDs/top10 giữ nguyên trong JSON.

## Trình duyệt

| Viewport | LCP ms | CLS | INP lab candidate ms |
|---:|---:|---:|---:|
{lab}

Một lượt Chrome local mỗi kích thước, không throttle; INP chỉ largest observed EventTiming trên typing/focus ngắn, null nếu không có entry≥16ms. Không gọi là field INP/SLA. Ảnh screenshot `home-*.png`, `products-*.png`, detail/checkout/order/image-search390 trong cùng thư mục. Body overflow false và không pageerror trong lượt đạt. Screenshot pilot đầu giữ riêng, không phải ảnh nghiệm thu cuối.

## Lỗi đã gặp và xử lý

Swatch bị map sofa và hai logo/placeholder được phát hiện khi nhìn UI/contact sheets; dry-run từ chối, chuyển pilot đó về nháp, sửa mapping rồi replay từ cache. Import CLIP constant sai module trong harness đã sửa trước chạy thành công. ESLint chạy từ root không tìm config; chạy lại đúng apps/web đạt. Docker Desktop từng dừng giữa audit: lần đó không tính là kết quả, giữ log lỗi rồi đổi tên giữ lại hai thư mục chỉ chứa socket runtime (run và docker-secrets-engine), khởi động lại với volume cũ và chạy lại. Không reset dữ liệu. Clean-start mới ở profile demo_seed kiểm migration/seed/checkout tương thích trên project riêng; catalog real318 được audit/import/replay riêng, không gọi clean seed50 là kiểm quy mô M8. Các lỗi browser/harness khác nếu có được giữ trong ignored artifacts; kết quả cuối là `browser.json`.

## Tài nguyên thực đo

Snapshot cuối lượt benchmark, trước rebuild bàn giao; Docker memory usage, không phải peak RSS hay điện năng:

| Container | Memory usage / limit | CPU tại snapshot |
|---|---|---|
{memory}

Dung lượng dataset riêng M8: private {storage["data/private/m8"]["bytes"]:,} bytes/{storage["data/private/m8"]["files"]} tệp; public WebP {storage["data/catalog/images"]["bytes"]:,} bytes/{storage["data/catalog/images"]["files"]} tệp. Tổng {(storage["data/private/m8"]["bytes"] + storage["data/catalog/images"]["bytes"]) / 1024 / 1024:.2f} MiB, không gồm model có sẵn, Docker image/volume và bằng chứng. Không gọi dung lượng cuối là dưới 200MB. Xem `resources.json`, `storage.json`.

## Giới hạn

Giá và hạn mức đặt thử mô phỏng; không chào bán/giao hàng/thanh toán thật. ASR M7 còn yếu, Chrome on-device thử nghiệm, TC2 vẫn chờ tệp thật. Không thêm text semantic weights hoặc API trả phí. Số đo snapshot/RSS không gọi là peak memory. Quy mô public cuối {audit["published_products"]} sản phẩm, không tự suy ra tốc độ ở1000/3000.
""",
    )
    put(
        "M8_COMPLETION_AUDIT.md",
        f"""
# M8 — bàn giao

## Kết quả

- Catalog profile real_demo: **{audit["stored_real_records"]} bản ghi lưu, {audit["published_products"]} sản phẩm public, {audit["working_photos"]} ảnh đúng hash, {audit["indexed_photos"]} vector tương thích**. Metadata/ảnh Amazon Berkeley Objects (ABO) CC-BY-4.0; nguồn và thay đổi hiển thị trong UI, xem [review nguồn/license](M8_DATASET_SOURCES.md). 3 bản ghi giữ nháp sau QC.
- Nguồn thật tách fixture M7; offer/đặt thử có nhãn riêng, không giả merchant price/stock/reviews/discount.
- Marketplace header/tìm kiếm, home, category grid, listing/filter drawer/sort/pagination, PDP gallery/zoom/related, cart/checkout, sources/help và responsive360–1440. Text/voice/image dùng pipeline hiện có.
- Backend **{tests[1]} test đạt**; browser {len(browser["results"])} nhóm đạt; xem [test report](M8_TEST_REPORT.md), [dataset audit](M8_DATASET_AUDIT.md), [nguồn](M8_DATASET_SOURCES.md).

## Tệp và trang

Danh sách chính xác ở [M8_CHANGED_FILES](M8_CHANGED_FILES.md), ảnh/ID/hash ở evidence/m8/catalog-manifest.json. Các trang: home, products/list/detail, search/text/voice/image, cart/checkout, account/orders, help/sources và quản lý read-only.

## Chạy

Mở http://localhost:3000 · API http://localhost:8000/docs. Stack hiện dùng DATA_PROFILE=real_demo, LOCAL_ONLY=true. Lệnh tái tạo nhập/index/đo ở [M8_SEARCH_REINDEX](M8_SEARCH_REINDEX.md); khởi động Docker không tải model/dataset ngầm.

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait
.\\.venv\\Scripts\\python.exe -m pytest apps/api/tests -q --junitxml=docs/evidence/m8/pytest.xml
.\\.venv\\Scripts\\python.exe benchmarks/scripts/m8_browser.py
```

Trước pytest, TEST_DATABASE_URL phải trỏ tới database riêng hoodoomart_test như RUNBOOK; không dùng URL database chính. Setup/import/index đầy đủ tại README và M8_SEARCH_REINDEX.

## Số đo bàn giao

Search TCP p95 tại concurrency1: {text["groups"][0]["tcp"]["p95_ms"]}ms; ảnh warm HTTP p95 {image["warm_http"]["p95_ms"]}ms, Recall@10={image["recall"]["10"] if "10" in image["recall"] else image["recall"]}. Cold/cache/concurrency và LCP/CLS lab từng viewport có phạm vi, qrels và kết quả gốc trong M8_TEST_REPORT; không gọi là SLA.

## Phần còn giới hạn

Chưa có catalog thật1000/3000 hoặc đủ34 leaf trong hồ sơ mới; thời trang chủ yếu giày dép. Không chứng minh smartphone shopping quality bằng source-photo qrels. TC2 vẫn chờ audio người dùng. Không gọi bản này là triển khai production Internet; thanh toán/vận chuyển thật nằm ngoài phạm vi. Báo cáo M7 giữ nguyên trạng thái nghiệm thu lịch sử.
""",
    )
    print("M8 reports generated from current evidence")


if __name__ == "__main__":
    main()
