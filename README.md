# HoodooMart

## Voice hiện tại — PhoWhisper-base int8

Đã nâng cấp model tiếng Việt và sửa cấu hình không timestamp. Trên29 câu mới khóa trước đánh giá, WER36,56%→7,53%; đây là giọng đọc, có trùng speaker, chưa chứng minh đúng mọi ngữ cảnh/micro thật. Chạy CPU cục bộ, không API trả phí; giữ câu gốc và gợi ý từ catalog cần xác nhận.157 unit API,187 integration,20 worker,20 benchmark tests và Chrome đạt. [Báo cáo, nguồn model và rollback](docs/VOICE_UPGRADE_REPORT.md).

## Unit test và chất lượng search

Chạy offline: `.\.venv\Scripts\python.exe -m pytest apps/api/unit_tests -q`; tại apps/web chạy `npm run test:unit` bằng Node24. Có72 unit backend và20 unit frontend;187 integration backend dùng DB test riêng. Đã sửa giá nói/từ đồng dạng và thêm gợi ý voice cần xác nhận; không tự thay câu nhận được. [Báo cáo chất lượng](docs/SEARCH_QUALITY_REPORT.md) phân biệt test logic với lỗi nghe Whisper base còn lại.

## Tìm kiếm ngay trên trang — 2026-10-23

Ở ô search trên header: gõ chữ và Enter, bấm **micro** để thu trực tiếp, hoặc bấm **camera** để chọn ảnh. Có thể **Ctrl+V ảnh** vào ô search/Dialog hoặc kéo thả ảnh. Kết quả hiển thị tại chỗ, không đổi trang. Voice tự nhận thành chữ khi dừng; kiểm tra/sửa câu rồi bấm Tìm. Đóng/hủy/ẩn tab/chuyển trang sẽ nhả micro; không tự bật khi mở web.

Đã kiểm **183 backend tests**, production build và Chrome ở5 kích thước màn hình. ASR kiểm bằng Chrome fake microphone phát clip người thật, chưa phải micro vật lý/TC2. Hướng dẫn, lệnh và bằng chứng: [INLINE_SEARCH_REPORT](docs/INLINE_SEARCH_REPORT.md).

## Hoàn thiện marketplace và AI — 2026-10-23

Trang chủ/bộ chọn danh mục được làm gọn theo bố cục marketplace tham khảo Shopee. Mở [Trợ lý chọn sản phẩm](http://localhost:3000/assistant): tìm từ mô tả hình dáng bằng text tower OpenCLIP có sẵn, giữ danh mục/ngân sách, phân trang và so sánh tối đa3 sản phẩm từ dữ liệu công khai. Ảnh và giọng nói vẫn dùng suy luận cục bộ; không tải weights mới hoặc dùng API trả phí. Mô tả Việt dùng từ vựng hữu hạn, không phải chatbot sinh nội dung. Kết quả/giới hạn/lệnh tái kiểm: [MARKETPLACE_AI_REPORT](docs/MARKETPLACE_AI_REPORT.md).

```powershell
.\.venv\Scripts\python.exe benchmarks/scripts/marketplace_ai_runtime.py
.\.venv\Scripts\python.exe benchmarks/scripts/marketplace_ai_browser.py
.\.venv\Scripts\python.exe benchmarks/scripts/marketplace_ai_regression.py
```

Chạy tuần tự sau build, dùng chứng cứ mới tại docs/evidence/marketplace-ai. TC2 vẫn chờ tệp âm thanh người dùng.

Marketplace tiếng Việt chạy cục bộ: Next.js → FastAPI → PostgreSQL/pgvector và một worker OpenCLIP/Whisper CPU. `LOCAL_ONLY=true`, không API suy luận trả phí.

## M8 hiện tại

**318 sản phẩm public, 624 ảnh nguồn hợp lệ và 624 vector tương thích.** Metadata/ảnh từ Amazon Berkeley Objects, CC BY 4.0, có ghi nguồn và lưu tên gốc. Giá, hạn mức đặt thử và đơn hàng được mô phỏng riêng; không phải giá/tồn kho của Amazon, không có thanh toán/giao hàng thật.

- Header tìm kiếm văn bản/giọng/ảnh, danh mục API, storefront responsive, bộ lọc URL, sorting/pagination.
- Gallery ảnh/phóng to, thông số nguồn, related products, giỏ/quantity/remove và checkout an toàn.
- Quyền ảnh/source/hash/revision, import có review/dry-run/replay, chỉ mục offline tăng dần; fixture M7 giữ trong hồ sơ riêng.
- Tài khoản/CSRF/ownership/giữ và nhả kho vẫn được kiểm. ASR còn giới hạn; **TC2 vẫn chờ tệp thật của người dùng**.

Mở [ứng dụng](http://localhost:3000) · [API](http://localhost:8000/docs).

## Chạy trên máy hiện tại

PowerShell 7, Docker Desktop Linux engine. Dataset/model đã có trong phiên làm việc này:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait
```

`.env` hiện chọn `DATA_PROFILE=real_demo`; các thông số khác và dữ liệu đã được giữ nguyên. Không reset/xóa volume để sửa lỗi.

## Tái tạo catalog đã duyệt trên máy mới

```powershell
.\scripts\setup.ps1
# Chỉ đổi profile, giữ credentials do setup sinh:
(Get-Content .env) -replace '^DATA_PROFILE=.*$', 'DATA_PROFILE=real_demo' | Set-Content .env -Encoding utf8
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait
.\.venv\Scripts\python.exe data_pipeline/abo.py acquire --reviewed
.\.venv\Scripts\python.exe data_pipeline/abo.py dry-run
.\.venv\Scripts\python.exe data_pipeline/abo.py import
.\.venv\Scripts\python.exe scripts/index_real_images.py
```

`--reviewed` dùng đúng318 external IDs đã duyệt, không lấy ngẫu nhiên320 bản ghi mới. Tải chọn lọc từ nguồn chính thức, cache/partial và hash được kiểm. Trọng số không tự tải: nếu máy mới chưa có models, đọc dung lượng/giấy phép và bước đồng ý trong [RUNBOOK](docs/RUNBOOK.md) trước khi dùng `scripts/download_models.py`. Catalog/text/cart vẫn hoạt động khi chưa có model; ảnh/ASR báo thiếu model.

Đăng ký tài khoản trên giao diện để đặt thử. Không có mật khẩu quản trị mặc định. Kênh quản lý real_demo được ghi rõ chỉ đọc; nhập mới phải qua review nguồn/ảnh. `demo_seed` vẫn dành cho fixture và thao tác M6 riêng.

## Kiểm thử và đo

```powershell
.\.venv\Scripts\python.exe -m ruff check apps/api apps/inference scripts data_pipeline benchmarks/scripts
.\.venv\Scripts\python.exe -m mypy --config-file apps/api/pyproject.toml apps/api/app
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q --junitxml=docs/evidence/m8/pytest.xml
.\.venv\Scripts\python.exe benchmarks/scripts/m8_evaluate.py audit
.\.venv\Scripts\python.exe benchmarks/scripts/m8_evaluate.py prepare
# Đo một lượt mới, không chạy build/test đồng thời:
docker compose --env-file .env -f infra/docker-compose.yml restart api inference
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait api inference
.\.venv\Scripts\python.exe benchmarks/scripts/m8_evaluate.py cold
.\.venv\Scripts\python.exe benchmarks/scripts/m8_evaluate.py measure
.\.venv\Scripts\python.exe benchmarks/scripts/m8_browser.py
.\.venv\Scripts\python.exe benchmarks/scripts/m8_media_checks.py
# Clean migration/seed/checkout compatibility trên DB/project riêng, không ghi lại report M7:
.\scripts\verify-clean.ps1 -ReportPath docs/evidence/m8/clean-start.json
```

Tests chỉ dùng `TEST_DATABASE_URL` riêng có hậu tố `_test`. Không chạy benchmark và pytest đồng thời. Cold/warm đo riêng; xem lệnh restart/health và phạm vi qrels tại [M8_SEARCH_REINDEX](docs/M8_SEARCH_REINDEX.md). Không dùng số M7 làm số đo M8.

## Bàn giao

- [Nghiệm thu M8](docs/M8_COMPLETION_AUDIT.md) · [Tệp đã thay đổi](docs/M8_CHANGED_FILES.md)
- [Nguồn và quyền ảnh](docs/M8_DATASET_SOURCES.md) · [Kiểm toán dữ liệu](docs/M8_DATASET_AUDIT.md)
- [Thiết kế UI](docs/M8_UI_UX_SPEC.md) · [Pipeline ảnh](docs/M8_IMAGE_PIPELINE.md) · [Nhập/chỉ mục/phục hồi](docs/M8_SEARCH_REINDEX.md)
- [Kết quả test và benchmark](docs/M8_TEST_REPORT.md) · [Tiến độ](docs/PROGRESS.md)
- [Kiến trúc](docs/ARCHITECTURE.md) · [Schema](docs/DATA_DICTIONARY.md) · [API](docs/API_CONTRACTS.md)
- Lịch sử: [M7 audit](docs/M7_COMPLETION_AUDIT.md), [slide audit](docs/SLIDE_AUDIT.md), [lựa chọn nhận giọng](docs/INFERENCE_OPTIONS.md).

Giới hạn: catalog thật chưa mở rộng1000/3000; thời trang chủ yếu giày dép. Nhãn relevance ảnh là cùng source product ID, chưa là nghiên cứu người dùng/ảnh điện thoại. CPU/RAM/đĩa vẫn được sử dụng; miễn phí API không đồng nghĩa không tốn tài nguyên. Không đưa `.env`, `models/`, `data/private/`, hồ sơ trình duyệt hay log nhạy cảm lên kho công khai.
