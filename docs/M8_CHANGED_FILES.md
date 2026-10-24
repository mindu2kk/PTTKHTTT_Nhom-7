# M8 — tệp thay đổi

Thư mục không có Git tại thời điểm bắt đầu; đây là danh sách tệp đã sửa/tạo trong M8, không phải `git diff`. Tệp MD/PDF đề bài M0–M7 và báo cáo nghiệm thu M7 được giữ nguyên.

## Backend và dữ liệu

- `apps/api/app/core/config.py`, `apps/api/app/core/dependencies.py`
- `apps/api/app/domain/catalog.py`, `apps/api/app/api/v1/catalog.py`
- `apps/api/app/infrastructure/models.py`, `catalog.py`, `vectors.py`, `commerce.py`
- `apps/api/app/infrastructure/real_catalog.py`, `abo_mapping.py` (mới)
- `apps/api/app/main.py`, `apps/api/Dockerfile`
- `apps/api/alembic/versions/0005_real_catalog.py` (mới)
- `apps/api/tests/test_real_catalog.py` (mới)
- `data_pipeline/abo.py`, `scripts/index_real_images.py`, `scripts/report_m8.py` (mới)
- `data/sources/abo-rights.json`, `abo-image-qc.json`, `abo-selection.json` (mới)
- `data/catalog/images/`: 624 WebP chính/gallery +624 thumbnail320 được tham chiếu. Tên/ID/hash chính xác tại `docs/evidence/m8/catalog-manifest.json`. Raw, cache và ảnh loại ở `data/private/m8`, không phải public assets.

## Frontend

- `apps/web/src/app/page.tsx`, `layout.tsx`, `marketplace.css` (CSS mới)
- `apps/web/src/app/products/page.tsx`, `products/[slug]/page.tsx`
- `apps/web/src/app/help/page.tsx`, `sources/page.tsx` (mới)
- `apps/web/src/components/site-header.tsx`, `search-bar.tsx`, `product-card.tsx`
- `apps/web/src/components/product-photo.tsx`, `product-gallery.tsx`, `filter-panel.tsx`, `catalog-skeleton.tsx` (mới)
- `apps/web/src/components/add-to-cart.tsx`, `cart-view.tsx`, `manage-products.tsx`
- `apps/web/src/components/ui/dialog.tsx`, `ui/sheet.tsx` (nhãn Đóng tiếng Việt)
- `apps/web/src/lib/schema.ts`, `docs/openapi.json` (sinh lại)

## Vận hành, kiểm thử, tài liệu

- `infra/docker-compose.yml`, `.dockerignore`; `.env` chỉ đổi DATA_PROFILE, không công khai credentials.
- `scripts/verify-clean.ps1`, `scripts/benchmark-http.ps1`: chọn demo_seed rõ cho harness M7 riêng, khôi phục biến môi trường; clean report có thể ghi tách M8.
- `benchmarks/scripts/m8_browser.py`, `m8_evaluate.py`, `m8_media_checks.py` (mới)
- `benchmarks/scripts/m8_structured_data.py` (mới): kiểm Chrome sau build cuối, giá mô phỏng/JSON-LD và HTTP404.
- `README.md`, `docs/PROGRESS.md`, `IMPLEMENTATION_PLAN.md`, `ARCHITECTURE.md`, `DATA_DICTIONARY.md`, `API_CONTRACTS.md`, `DATA_SOURCES.md`
- `docs/M8_IMPLEMENTATION_PLAN.md`, `M8_DATASET_SOURCES.md`, `M8_DATASET_AUDIT.md`, `M8_UI_UX_SPEC.md`, `M8_IMAGE_PIPELINE.md`, `M8_SEARCH_REINDEX.md`, `M8_TEST_REPORT.md`, `M8_COMPLETION_AUDIT.md`, tệp này.
- `docs/evidence/m8/`: logs/JSON/JUnit/qrels/screenshot/EXPLAIN/snapshots mới. `artifacts/m8-*.log`: log chi tiết cục bộ được bỏ qua khi quản lý mã nguồn.

## Xử lý Docker Desktop của môi trường

Lỗi AF_UNIX socket khiến engine dừng. Các thư mục **chỉ chứa socket runtime** đã được đổi tên giữ lại trong `%LOCALAPPDATA%` với hậu tố `.m8-stale-...`; Docker tạo runtime mới và khởi động lại. Đã kiểm tra đường dẫn/tên và nội dung trước khi đổi tên. Không có thay đổi cấu hình Docker, không xóa dữ liệu engine hoặc volume. Snapshot trạng thái và hướng xử lý ở M8_TEST_REPORT.
