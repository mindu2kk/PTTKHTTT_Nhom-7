# Kế hoạch và trạng thái M0–M8

## Bổ sung 100 sản phẩm nam — 2026-10-27

Hoàn tất nhập100 sản phẩm Rhodi đã được người dùng duyệt quyền, public catalog119
và19 danh mục. Giữ nguyên mọi hàng cũ qua đối chiếu hash, thêm119 vector ảnh public,
kiểm5 truy vấn chữ và một truy vấn cùng ảnh/top1;42 tests liên quan và mypy45 file đạt.
Không thay gate chất lượng ASR hay benchmark ảnh khác góc. Dữ liệu, lỗi vận hành,
giới hạn và lệnh tại [MENSWEAR_EXPANSION_100](MENSWEAR_EXPANSION_100.md).

## Top-K tìm ảnh — 2026-10-26

Đã thêm Top-K1–100 cho cả hai UI ảnh và API, giới hạn trước phân trang.
504 backend tests, lint/type/build và Chrome thật đạt; không thay gate chất
lượng model. Phạm vi/lệnh/evidence tại [IMAGE_TOP_K](IMAGE_TOP_K.md).

## Dọn code media — 2026-10-26

Đã refactor phần media vừa thay đổi, tái dùng validator/encoder và gom checksum;
giữ cổng quyền/giới hạn upload. 48 backend/script tests +22 worker tests và
lint/build/replay/Chrome đạt; không đổi gate milestone. Chi tiết:
[MEDIA_CODE_CLEANUP](MEDIA_CODE_CLEANUP.md).

## Bật tìm ảnh cho catalog Hoodoo — 2026-10-26

Đã tải OpenCLIP sau consent, index20 ảnh của catalog hiện tại và kiểm replay
không encode trùng. Hỗ trợ URL gallery đã duyệt bằng public catalog gate.
41 tests + Ruff và Chrome model thật đạt; không đổi gate benchmark M4/M8.
Sau thêm/đổi ảnh cần reindex. Chi tiết: [LOCAL_IMAGE_SEARCH](LOCAL_IMAGE_SEARCH.md).

## Sửa bản ghi nhỏ và kiểm tra micro — 2026-10-26

Đã sửa cổng âm lượng trước ASR, thêm chọn micro/mức âm cho hai giao diện voice.
22 worker tests, 20 frontend tests, lint/build và Chrome model thật đạt;
web/inference healthy. Micro vật lý chưa kiểm. Không thay trạng thái các gate
milestone từ kết quả này. Evidence: [LOCAL_VOICE_SETUP](LOCAL_VOICE_SETUP.md).

## Bật lại voice cục bộ trên máy hiện tại — 2026-10-26

Người dùng đã hủy Google API, chọn thư viện cục bộ và đồng ý tải một model.
Đã tải/checksum/chuyển PhoWhisper-base int8 bằng converter sẵn có, bật profile
phowhisper-base và giữ LOCAL_ONLY=true. Model load thật; 137 tests liên quan +20
worker tests và Chrome MediaRecorder→ASR→sửa tay→tìm đạt. Audio kiểm tra là eSpeak
qua micro Chrome mô phỏng, chưa kiểm micro vật lý. Không tải CLIP/model khác.
Lệnh, evidence và giới hạn: [LOCAL_VOICE_SETUP](LOCAL_VOICE_SETUP.md).

## Quản trị sản phẩm và nhiều URL ảnh — 2026-10-26

Admin trong real_demo đã thêm/sửa/xuất bản/ẩn được sản phẩm; chỉnh kho theo size.
Ảnh nhập bằng nhiều URL Postimages, mỗi dòng một ảnh, ảnh đầu làm ảnh bìa;
kiểm quyền/host/MIME/bytes/pixels, preview và lưu thứ tự gallery qua migration0009.
Đã cấp role admin cho tài khoản người dùng chỉ định, giữ mật khẩu.
480 backend tests +20 frontend tests, Ruff/mypy/ESLint/build và Chrome thực tế đạt.
Có backup, không reset dữ liệu; QA tạm đã dọn. Hướng dẫn/phạm vi/lệnh/rollback:
[ADMIN_PRODUCTS](ADMIN_PRODUCTS.md).

## Chọn size theo sơ đồ VPP — 2026-10-26

Đã áp dụng Alembic `0008_product_sizes`, thêm kho theo S/M/L/XL/XXL/F;
giỏ và chi tiết đơn liên kết product_size, giữ/nhả/trừ kho theo size.
UI chi tiết/giỏ/đơn và fallback không JavaScript đã cập nhật.
Giữ nguyên sản phẩm, giỏ, đơn và tổng kho cũ; backup trước migration.
463 backend tests (266 unit +197 integration), 20 frontend tests, Ruff/mypy,
ESLint, production/Docker build và Chrome desktop/mobile đạt.
Bốn dịch vụ healthy; phạm vi phân bổ demo/đơn lịch sử/rollback tại
[PRODUCT_SIZES](PRODUCT_SIZES.md).

## Nhập DataShopping đầy đủ — 2026-10-26

Đã thêm18 sản phẩm Rhodi, tái sử dụng1; public catalog19 sản phẩm/19 ảnh URL trực tiếp.
Kho thiếu được cấp demo ngẫu nhiên5–20 theo người dùng; bản ghi cũ on_hand8/reserved1 giữ nguyên.
Size/màu nhiều giá trị giữ đầy đủ trong JSON options, chưa tách SKU/kho theo biến thể.
19 tests import/rollback đạt, mypy42files/build đạt; Chrome19 ảnh/phân trang/mobile đạt.
Backup, lệnh, phạm vi tại [SHOPPING_BULK_IMPORT](SHOPPING_BULK_IMPORT.md).

## Banner ảnh trượt trang chủ — 2026-10-26

Đã thay banner cũ bằng3 ảnh người dùng cung cấp trong `Pictures/fashionImage/main-image`,
copy nguyên bản vào `apps/web/public/images/campaign/menswear/`, giữ watermark/credit.
Chữ/nút HTML tiếng Việt trên nền tối, ảnh bên phải desktop và phía trên mobile;
trước/sau/dots/keyboard/swipe, tự chuyển6s, tạm dừng khi hover/focus/tabẩn hoặc người dùng thao tác.
Tôn trọng prefers-reduced-motion (không tự chạy/không transition); inactive slides inert.
Docker frontend build/TypeScript đạt; `artifacts/verify_home_carousel.py` qua Chrome ở1440/768/390/360px,
kiểm3 ảnh tải được, autoplay/manual pause/wrap/dots/keyboard/CTA/swipe mô phỏng/reduced motion,
không tràn ngang. Đã xem ảnh desktop/mobile tại `artifacts/campaign-*.png`.
Lượt harness đầu thiếu TouchInit.identifier, đã sửa mô phỏng và chạy lại đạt; không phải lỗi UI.
Trang sources cập nhật nguồn ảnh banner. Không thay database, catalog hay pipeline AI.

## Mẫu Rhodi dùng URL ảnh trực tiếp — 2026-10-26

Đã nhập một bản ghi đã được người dùng xác nhận quyền: `rhodi-p11847`, profile real_demo.
Ảnh Postimages render trực tiếp200/640x800 trên catalog/detail/zoom/mobile; không lưu ảnh vào project.
264 unit +62 integration liên quan đạt; Ruff/mypy/build đạt. DB host chuyển sang15432 vì55432 bị Windows loại trừ.
Nguồn Rhodi riêng, không gán ABO; chi tiết tại [SHOP_SAMPLE_PREVIEW](SHOP_SAMPLE_PREVIEW.md).

## Danh mục thời trang nam — 2026-10-26

Đã áp dụng migration `0007_menswear_categories`: 1 gốc, 3 nhóm, 19 mục lá theo ảnh người dùng.
Chỉ hiển thị cây mới; 49 mục cũ và 55 sản phẩm được giữ, chưa gán lại/chưa nhập sản phẩm mới.
Đồng bộ menu/filter/search và kiểm tra quản lý; 248 unit + 193 integration đạt, Ruff/mypy/build/Alembic check đạt.
Backup, ID danh mục, rollback và giới hạn tại [MENSWEAR_CATEGORIES](MENSWEAR_CATEGORIES.md).

## Đối chiếu backend với thiết kế — 2026-10-25

Đã sửa ranh giới router/application, điều kiện fallback sau ranking, ưu tiên brand/giá,
history đa phương thức và kiểm tra tồn kho giỏ theo [BACKEND_DESIGN_ALIGNMENT](BACKEND_DESIGN_ALIGNMENT.md).
Revision mã mới là `0006_search_trace`; chưa áp dụng vào DB chính. Phần M8 bên dưới là
trạng thái lịch sử ở revision `0005_real_catalog`. Phạm vi semantic tổng quát/payment thật
và TC2 chưa được nghiệm thu thêm trong đợt này.

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
