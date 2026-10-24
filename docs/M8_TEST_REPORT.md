# M8 — kiểm thử và số đo mới

Ngày 2026-10-22, cùng máy Windows/Core i3/RAM như `evidence/hardware.json`; Docker PostgreSQL/API/worker CPU, OpenCLIP revision giữ nguyên. Không dùng số M7 làm kết quả M8. File thay đổi: M8_CHANGED_FILES.md; ảnh đối chiếu trước/sau và qrels giữ trong evidence/m8.

## Lệnh và kết quả

- Baseline trước sửa: `scripts/verify.ps1` — 127 passed/49.43s (`evidence/m8/baseline.txt`).
- Sau sửa: `.venv\Scripts\python.exe -m pytest apps/api/tests -q --junitxml=docs/evidence/m8/pytest.xml` — **151 passed/25.72s**. Gồm parser/rights/upload/order/CSRF/IDOR/stock race cũ và import/license/ID/mapping/ảnh hỏng/replay/revision/multiple-gallery/revoked-photo mới.
- Ruff/format (95 tệp), strict mypy37 source files, frontend ESLint/TypeScript, Alembic check và Docker build: log riêng cùng thư mục hoặc `artifacts/m8-web-final-build.log`; không dùng việc tạo file log thay cho exit0.
- Import/dry-run/replay/index/replay: `data_pipeline/abo.py` và `scripts/index_real_images.py`; 626 ảnh trước final QC, encode/update 604, skip 22; lần index lặp sau final QC encode0/skip624.
- `benchmarks/scripts/m8_browser.py`: 8 nhóm kết quả đạt — năm viewport, gallery/zoom, cart qty/remove/buy-now, đăng ký/checkout/owner/cancel nhả kho, voice correction, image thật/invalid/empty/404. Voice là câu sửa được nhập, **không phải TC2 ASR**. Không mock catalog/checkout. Thêm actual BFF ASR trên1 VIVOS human clip và corrupt image/audio422, invalid cart cookie422, no-JS cart303 trong media-checks.json; không dùng clip đó làm TC2.
- `m8_evaluate.py prepare/audit/cold/measure`: hash/ảnh/index SQL thật, EXPLAIN thật, HTTP TCP thật. Qrels text là oracle cấu trúc category từ source, không human semantic judgments.
- Sau build cuối, `benchmarks/scripts/m8_structured_data.py` đạt trên Chrome thật: Product JSON-LD không có merchant Offer/InStock cho real_demo, giá đặt thử gắn PropertyValue đúng API, nút/số lượng còn dùng được và sản phẩm thiếu trả404. Bằng chứng `structured-data.json`.

## HTTP trên 318 sản phẩm public

| Đồng thời | Search requests | Service p95 ms | TCP p50 ms | TCP p95 ms | Grid TCP p95 ms |
|---:|---:|---:|---:|---:|---:|
| 1 | 114 | 60.122 | 49.594 | 78.122 | 60.624 |
| 5 | 114 | 96.857 | 77.235 | 150.379 | 108.001 |
| 10 | 114 | 168.522 | 166.802 | 260.417 | 316.136 |

Mỗi nhóm có thêm60 grid requests. Hard category leaks: [0, 0, 0]. Precision@10/Recall@10/NDCG@10 và kết quả từng câu trong `text-http.json`; category ít hơn10 relevant items có trần Precision@10 thấp, không đổi mẫu số để làm đẹp. Không có benchmark real1000/3000 trong M8.

## Ảnh

Process-cold sau restart worker riêng, API cache hit=false, cache OS không được xóa: HTTP200, 14606.386ms. Warm full HTTP: **p50=522.811ms, p95=1257.503ms**, 20 ảnh query nguồn khác ID/bytes, không nằm trong gallery; warmup riêng không đưa vào số đo. Mọi measured query cached=false.

Recall@1/5/10: {'1': 0.65, '5': 0.85, '10': 0.95}; NDCG@10=0.7941. Nhãn relevance là cùng source product ID, chưa có người dùng chấm. Đã nhìn contact sheet, loại explanatory line drawings khỏi bộ query. Ảnh góc khác/detail/lifestyle và phụ kiện; không kết luận điện thoại thực tế/occlusion/cross-brand đã được đánh giá đầy đủ. Failure IDs/top10 giữ nguyên trong JSON.

## Trình duyệt

| Viewport | LCP ms | CLS | INP lab candidate ms |
|---:|---:|---:|---:|
| 360 | 464.0 | 0.00000 | 16 |
| 390 | 248.0 | 0.00000 | 24 |
| 768 | 264.0 | 0.00000 | 16 |
| 1280 | 296.0 | 0.00000 | 32 |
| 1440 | 252.0 | 0.00000 | None |

Một lượt Chrome local mỗi kích thước, không throttle; INP chỉ largest observed EventTiming trên typing/focus ngắn, null nếu không có entry≥16ms. Không gọi là field INP/SLA. Ảnh screenshot `home-*.png`, `products-*.png`, detail/checkout/order/image-search390 trong cùng thư mục. Body overflow false và không pageerror trong lượt đạt. Screenshot pilot đầu giữ riêng, không phải ảnh nghiệm thu cuối.

## Lỗi đã gặp và xử lý

Swatch bị map sofa và hai logo/placeholder được phát hiện khi nhìn UI/contact sheets; dry-run từ chối, chuyển pilot đó về nháp, sửa mapping rồi replay từ cache. Import CLIP constant sai module trong harness đã sửa trước chạy thành công. ESLint chạy từ root không tìm config; chạy lại đúng apps/web đạt. Docker Desktop từng dừng giữa audit: lần đó không tính là kết quả, giữ log lỗi rồi đổi tên giữ lại hai thư mục chỉ chứa socket runtime (run và docker-secrets-engine), khởi động lại với volume cũ và chạy lại. Không reset dữ liệu. Clean-start mới ở profile demo_seed kiểm migration/seed/checkout tương thích trên project riêng; catalog real318 được audit/import/replay riêng, không gọi clean seed50 là kiểm quy mô M8. Các lỗi browser/harness khác nếu có được giữ trong ignored artifacts; kết quả cuối là `browser.json`.

## Tài nguyên thực đo

Snapshot cuối lượt benchmark, trước rebuild bàn giao; Docker memory usage, không phải peak RSS hay điện năng:

| Container | Memory usage / limit | CPU tại snapshot |
|---|---|---|
| hoodoomart-api-1 | 77.42MiB / 7.621GiB | 38.94% |
| hoodoomart-web-1 | 102.6MiB / 7.621GiB | 0.13% |
| hoodoomart-inference-1 | 1.081GiB / 3GiB | 0.23% |
| hoodoomart-postgres-1 | 75.75MiB / 7.621GiB | 8.50% |

Dung lượng dataset riêng M8: private 247,216,686 bytes/657 tệp; public WebP 45,045,920 bytes/1248 tệp. Tổng 278.72 MiB, không gồm model có sẵn, Docker image/volume và bằng chứng. Không gọi dung lượng cuối là dưới 200MB. Xem `resources.json`, `storage.json`.

## Giới hạn

Giá và hạn mức đặt thử mô phỏng; không chào bán/giao hàng/thanh toán thật. ASR M7 còn yếu, Chrome on-device thử nghiệm, TC2 vẫn chờ tệp thật. Không thêm text semantic weights hoặc API trả phí. Số đo snapshot/RSS không gọi là peak memory. Quy mô public cuối 318 sản phẩm, không tự suy ra tốc độ ở1000/3000.
