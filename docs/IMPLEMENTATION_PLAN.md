# Kế hoạch và trạng thái M0–M8

## Nâng cấp ASR qua agent — 2026-10-23

Đã thực hiện [VOICE_UPGRADE_PLAN](VOICE_UPGRADE_PLAN.md): PhoWhisper-base có đồng ý riêng, conversion int8/integrity/local-only, sửa timestamp compatibility, frozen protocol V1/V2, public-catalog suggestions và rollout sau gate. V2 WER36,56%→7,53%; kiểm phần mềm/Chrome đạt. [VOICE_UPGRADE_REPORT](VOICE_UPGRADE_REPORT.md) giữ rõ các split, timing/RAM, hồi quy và TC2 còn mở.

## Search quality / unit tests — 2026-10-23

Đã thực hiện [SEARCH_QUALITY_PLAN](SEARCH_QUALITY_PLAN.md): suite offline riêng, hồi quy parser/giá/ngữ cảnh, voice gợi ý có xác nhận và đo decoder có đối chứng. Kết quả/giới hạn tại [SEARCH_QUALITY_REPORT](SEARCH_QUALITY_REPORT.md); chất lượng nghe của base chưa được coi là giải quyết.

## Search tại ô tìm kiếm — 2026-10-23

Thực hiện [INLINE_SEARCH_PLAN](INLINE_SEARCH_PLAN.md): Dialog/controller chung, text/ảnh/voice tại cùng URL, paste/picker, cleanup tracks/requests/blob và backend chuẩn hóa câu. Báo cáo/gate tại [INLINE_SEARCH_REPORT](INLINE_SEARCH_REPORT.md). Không thêm model, API ngoài, migration hay ghi raw media.

## Đợt hoàn thiện marketplace/AI — 2026-10-23

Đã triển khai theo [MARKETPLACE_AI_PLAN](MARKETPLACE_AI_PLAN.md): home/menu/account UI, text tower OpenCLIP trên gallery có sẵn, giữ bộ lọc/phân trang, so sánh qua public catalog, liên kết ảnh/giọng. 175 tests và hai bộ Chrome đạt; số đo mới/phạm vi ở [MARKETPLACE_AI_REPORT](MARKETPLACE_AI_REPORT.md). Mô tả Việt dùng từ vựng hữu hạn; không đổi phạm vi TC2/production, không tải weights hoặc nhập dữ liệu mới.

## M8 — đã thực hiện

Kế hoạch chi tiết tại [M8_IMPLEMENTATION_PLAN](M8_IMPLEMENTATION_PLAN.md). Đã hoàn tất cohort 318 sản phẩm/624 ảnh thật CC-BY-4.0, import có duyệt và replay không trùng, index gallery tăng dần, storefront marketplace và các luồng đặt thử. 151 backend tests và 8 nhóm Chrome đạt; báo cáo [M8_COMPLETION_AUDIT](M8_COMPLETION_AUDIT.md) ghi đủ số đo/giới hạn.

Migration hiện tại `0005_real_catalog`; một ảnh chính và nhiều ảnh gallery được hỗ trợ. Cây public real_demo 4/4/19, cây bài học cũ giữ riêng. Chưa mở rộng catalog thật1000/3000; TC2 nguyên câu vẫn chờ file, không đánh dấu toàn bộ nghiệm thu M7 đã đóng.

## Kế hoạch M0–M7 và kết quả lịch sử

Đã thực hiện theo thứ tự; nguồn chính là MD và PDF 57 trang trong `reference/`. Đối chiếu trang tại SLIDE_AUDIT; trạng thái thực tế tại PROGRESS, không dùng mô tả M1 cũ làm hiện trạng.

| Mốc | Kết quả triển khai | Gate còn mở |
|---|---|---|
| M0 | Audit, kiến trúc, traceability, nguồn, runbook | Không |
| M1 | PostgreSQL/25 bảng qua 4 migration, fixture gốc, quyền/provenance | Gate local đạt; một offer/variant/ảnh chính là phạm vi demo |
| M2 | Storefront/API, responsive, SSR/404/cart, form Zod | Gate browse/cart đạt; field INP không được tuyên bố |
| M3 | Text/parser/hard filters/soft ranking/consent-safe relaxation | TC1/TC4 đạt; semantic/hybrid là lựa chọn chưa triển khai |
| M4 | OpenCLIP thật/offline/QC; 25 ảnh đối tượng held-out + Fashion-MNIST | TC3 curated đạt; chưa chứng minh ảnh điện thoại/same-SKU thời trang |
| M5 | MediaRecorder/Whisper, VIVOS20 + ViMD9 + 5 ca stress, thử nghiệm on-device | Chờ tệp TC2 nguyên câu của người dùng; ASR còn yếu, mẫu nhỏ |
| M6 | Auth/ownership/cart/transaction/admin/import/history | Thanh toán/vận chuyển thật thuộc P2 |
| M7 | CPU Compose, regression, 3k/204 oracle + HTTP thật, security, handoff | Phần kỹ thuật đã kiểm; chưa đóng toàn bộ gate TC1–TC6 vì chờ TC2; không yêu cầu production/P2 |

## Quyết định phạm vi

- Giữ modular monolith, một worker inference CPU; không thêm Redis/Kubernetes/GPU vì chưa có bằng chứng cần thiết.
- Giữ tên HoodooMart; dữ liệu gốc do dự án tạo, không nhận là Tiki.
- TC4: màu văn bản giữ cứng cho tới khi người dùng cho phép nới; category/UI không nới. Course-v2 hiệu chỉnh hai giá có kiểm tra phiên bản, không ghi đè thay đổi người dùng.
- Hoàn thiện tính đúng/quyền/transaction trước chất lượng model và trang trí. Chất lượng model không được suy ra từ việc tải được weights hoặc tạo được pipeline.
