# M8 — bàn giao

## Kết quả

- Catalog profile real_demo: **321 bản ghi lưu, 318 sản phẩm public, 624 ảnh đúng hash, 624 vector tương thích**. Metadata/ảnh Amazon Berkeley Objects (ABO) CC-BY-4.0; nguồn và thay đổi hiển thị trong UI, xem [review nguồn/license](M8_DATASET_SOURCES.md). 3 bản ghi giữ nháp sau QC.
- Nguồn thật tách fixture M7; offer/đặt thử có nhãn riêng, không giả merchant price/stock/reviews/discount.
- Marketplace header/tìm kiếm, home, category grid, listing/filter drawer/sort/pagination, PDP gallery/zoom/related, cart/checkout, sources/help và responsive360–1440. Text/voice/image dùng pipeline hiện có.
- Backend **151 test đạt**; browser 8 nhóm đạt; xem [test report](M8_TEST_REPORT.md), [dataset audit](M8_DATASET_AUDIT.md), [nguồn](M8_DATASET_SOURCES.md).

## Tệp và trang

Danh sách chính xác ở [M8_CHANGED_FILES](M8_CHANGED_FILES.md), ảnh/ID/hash ở evidence/m8/catalog-manifest.json. Các trang: home, products/list/detail, search/text/voice/image, cart/checkout, account/orders, help/sources và quản lý read-only.

## Chạy

Mở http://localhost:3000 · API http://localhost:8000/docs. Stack hiện dùng DATA_PROFILE=real_demo, LOCAL_ONLY=true. Lệnh tái tạo nhập/index/đo ở [M8_SEARCH_REINDEX](M8_SEARCH_REINDEX.md); khởi động Docker không tải model/dataset ngầm.

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q --junitxml=docs/evidence/m8/pytest.xml
.\.venv\Scripts\python.exe benchmarks/scripts/m8_browser.py
```

Trước pytest, TEST_DATABASE_URL phải trỏ tới database riêng hoodoomart_test như RUNBOOK; không dùng URL database chính. Setup/import/index đầy đủ tại README và M8_SEARCH_REINDEX.

## Số đo bàn giao

Search TCP p95 tại concurrency1: 78.122ms; ảnh warm HTTP p95 1257.503ms, Recall@10=0.95. Cold/cache/concurrency và LCP/CLS lab từng viewport có phạm vi, qrels và kết quả gốc trong M8_TEST_REPORT; không gọi là SLA.

## Phần còn giới hạn

Chưa có catalog thật1000/3000 hoặc đủ34 leaf trong hồ sơ mới; thời trang chủ yếu giày dép. Không chứng minh smartphone shopping quality bằng source-photo qrels. TC2 vẫn chờ audio người dùng. Không gọi bản này là triển khai production Internet; thanh toán/vận chuyển thật nằm ngoài phạm vi. Báo cáo M7 giữ nguyên trạng thái nghiệm thu lịch sử.
