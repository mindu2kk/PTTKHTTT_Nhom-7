# Tiến độ hiện tại

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

Cập nhật ngày 2026-10-25; giữ nguyên ngày đo trong từng bằng chứng.

## Sửa backend theo sơ đồ và PDF — 2026-10-25

Router commerce/history đi qua application service; fallback dựa trên kết quả sau ranking/vector;
brand/giá đã nới tiếp tục là ưu tiên. Migration `0006_search_trace` bổ sung normalized query,
filters và điểm/rank thực tế; history ảnh/describe giữ opt-in, không lưu raw media. Giỏ hàng
từ chối vượt tồn kho và rollback. **387 tests đạt/23.56s** (196 unit + 191 integration),
Ruff/format và strict mypy 40 tệp đạt. Báo cáo đối chiếu, lệnh, kết quả và giới hạn tại
[BACKEND_DESIGN_ALIGNMENT](BACKEND_DESIGN_ALIGNMENT.md). Chưa migrate DB chính;
không coi semantic tổng quát hay các use case thương mại ngoài phạm vi hiện có là đã hoàn tất.

## Nhận giọng hiện tại — PhoWhisper-base int8

Đã triển khai qua3agent + tích hợp, user đồng ý riêng tải294MB model VinAI BSD-3-Clause. Pho chạy CPU2threads, đúng chế độ không timestamp, từ vựng gợi ý lấy catalog public; không auto-rewrite transcript/giá/màu/mã đơn. Bộ V2 gồm29 câu chưa giải mã trước khi khóa cấu hình: **WER36,56%→7,53%, CER17,55%→3,80%**. V2 có trùng speaker, chỉ VIVOS/giọng đọc; không nghiệm thu mọi giọng mua hàng/micro vật lý/TC2. Development VIVOS20 cũ23,92%→5,26% là số development, không trộn với V2.157 API unit +187 integration +20 worker +20 benchmark tests đạt; Chrome5viewport và actual MediaRecorder/ASR qua model mới đạt.4 dịch vụ healthy, model base cũ giữ rollback. [Báo cáo](VOICE_UPGRADE_REPORT.md), [kế hoạch/khóa đánh giá](VOICE_UPGRADE_PLAN.md).

## Unit test và sửa lỗi ngữ cảnh search — trước nâng cấp ASR

**72 unit backend,20 unit frontend và187 integration backend đạt ở lượt đó**. Sửa giá nói bằng chữ/chiều bất đẳng thức/khoảng giá và từ đồng dạng có dấu; voice giữ câu gốc, hiện warning và gợi ý hữu hạn cần xác nhận. Thử3 decoder settings không cải thiện cả hai nhóm audio nên giữ base ở lượt đó. Phạm vi, số đo và lệnh lịch sử tại [SEARCH_QUALITY_REPORT](SEARCH_QUALITY_REPORT.md). TC2/micro vật lý chưa nghiệm thu.

## Tích hợp search tại chỗ

Ô search hiện mở một Dialog dùng chung để nhập chữ, thu âm trực tiếp hoặc chọn/dán ảnh; không điều hướng khi tìm và xem kết quả. Thu âm tự chuyển thành chữ khi dừng, cho sửa rồi tìm cùng pipeline voice; mọi request giữ Origin/upload/ownership gates. Ảnh và audio chỉ giữ tạm, hủy/đóng/chuyển trang/tab ẩn nhả tài nguyên. Backend chuẩn hóa transcript1–300 ký tự, từ chối câu chỉ có khoảng trắng. Kiểm thử backend mới: **183 passed/98.10s**, log `evidence/inline-search/pytest.txt`. Luồng và phạm vi tại [INLINE_SEARCH_PLAN](INLINE_SEARCH_PLAN.md); báo cáo kết quả UI tại [INLINE_SEARCH_REPORT](INLINE_SEARCH_REPORT.md). TC2 vẫn chờ file thật; Chrome fake microphone/VIVOS không phải TC2.

## Thu gọn trang chủ theo ảnh người dùng

Đã bỏ hero nhiều chữ, thẻ giới thiệu AI/ảnh, thanh công cụ đóng khung, thẻ danh mục nhiều nội dung và dải tìm ảnh lặp. Trang chủ chuyển sang banner ảnh riêng không chữ, danh mục biểu tượng nhỏ và một lưới24 sản phẩm; header gọn hơn. Minh họa AI chỉ dùng trang trí, không vào catalog/index. Tệp ảnh/prompt/phạm vi tại [HOME_CLEANUP](HOME_CLEANUP.md); bằng chứng UI mới `evidence/home-cleanup/`. Kết quả AI/backend bên dưới là lịch sử kiểm trước thay đổi bố cục, không tuyên bố đã chạy lại toàn bộ tests.

## Hoàn thiện marketplace và AI — hiện tại

- Home/bố cục marketplace, menu danh mục có keyboard/focus, tài khoản theo phiên/role và logout thật; công cụ AI thống nhất trên desktop/mobile. Browser tham khảo cấu trúc trang chủ Shopee rồi gặp CAPTCHA; không nhận đã khảo sát backend nội bộ của Shopee.
- `/assistant`: mô tả hình dáng bằng text tower OpenCLIP đã có, giữ bộ lọc/ngân sách, phân trang và so sánh tối đa3 sản phẩm từ API công khai. Mapping Việt hữu hạn; không tải weights mới hoặc gọi suy luận ngoài máy.
- Sửa homograph “đồ” bị hiểu nhầm màu đỏ và cosine gần nhau bị ID quyết định thứ tự. **175 backend tests/52.67s đạt; 8 nhóm Chrome mới và 8 nhóm regression M8 đạt**, có cả image retrieval thật, checkout/ownership/cancel và logout mobile/desktop. TC2 vẫn chờ tệp thật, không tính câu gõ hoặc VIVOS clip thành TC2.
- Đo16 mô tả theo bộ từ vựng hữu hạn: top1 khớp nhóm16/16, P@5 trung bình0.85. 14 lượt không cache warm qua BFF: p50=219.197ms, p95=377.895ms; 2 lượt cache tương đương tách riêng. Proxy category nguồn, không human relevance/general Vietnamese quality. Lượt đầu20.44952s do load model; không cam kết mọi yêu cầu dưới1s.
- Truy vấn kiểm hiện trạng:318 sản phẩm,624 ảnh được duyệt/624 vector tương thích, LOCAL_ONLY=true. Giá/kho/đơn đặt thử mô phỏng và phạm vi nguồn M8 giữ nguyên. Báo cáo/tệp/lệnh/ảnh tại [MARKETPLACE_AI_REPORT](MARKETPLACE_AI_REPORT.md), bằng chứng mới `evidence/marketplace-ai/`; M7/M8 giữ lịch sử.

## M8 — hiện trạng sau nâng cấp

- Hồ sơ `real_demo`: **318 sản phẩm public, 624 ảnh thật được duyệt và 624 vector OpenCLIP tương thích**. Nguồn Amazon Berkeley Objects CC-BY-4.0; lưu riêng metadata thật và giá/hạn mức đặt thử mô phỏng. 3 bản ghi QC giữ nháp, không vào kết quả công khai. Không xóa dữ liệu M7 hay đơn người dùng.
- Marketplace cam đỏ: header tìm kiếm chung, home, danh mục, bộ lọc URL/mobile, sắp xếp/phân trang, gallery/zoom, giỏ và checkout mô phỏng, trang nguồn/trợ giúp. Quản lý catalog thật chỉ đọc; nhập qua pipeline có kiểm quyền, ID/hash và danh sách duyệt.
- **151 tests đạt/25.72s**, 8 nhóm Chrome đạt với 5 viewport 360/390/768/1280/1440. Build, lint, mypy, Alembic và kiểm tra ảnh/index có bằng chứng riêng. Khởi động sạch dùng project/DB riêng và fixture M7; không gọi đó là nhập sạch toàn catalog thật.
- Đo mới trên 318 sản phẩm: search TCP p95 78.122ms tại concurrency1; ảnh warm p95 1257.503ms trên 20 query khác gallery, Recall@10=0.95. Image process-cold 14606.386ms; cache OS chưa xóa. Số đo này không thay benchmark mô phỏng 3k của M7.
- Chạy tại http://localhost:3000; API http://localhost:8000/docs; `LOCAL_ONLY=true`, không API trả phí/trọng số mới. Chi tiết: [M8 completion](M8_COMPLETION_AUDIT.md), [test report](M8_TEST_REPORT.md), [dataset audit](M8_DATASET_AUDIT.md), [tệp thay đổi](M8_CHANGED_FILES.md).
- Giới hạn hiện tại: thời trang chủ yếu giày dép; cây public 4/4/19, chưa đủ34 leaf hay catalog thật1000/3000. Giá/kho/đơn mô phỏng; TC2 vẫn chờ tệp âm thanh thật, Chrome on-device thử nghiệm.

## Lịch sử M0–M7

Các kết quả và giới hạn bên dưới ghi lại thời điểm kết thúc M7. M8 đã bổ sung nhiều ảnh và migration0005; không diễn giải giới hạn một ảnh/4 migration của M7 thành trạng thái hiện tại.

### Completed

- M0–M1: đọc MD/PDF, đối chiếu trực tiếp, schema/migration/seed gốc có provenance và quyền dữ liệu.
- M2–M4: Next.js tiếng Việt, URL filters/facets thật, giỏ, text parser và relaxation có đồng ý; OpenCLIP CPU thật, pgvector được lọc trước theo quyền/danh mục/giá.
- M5: ghi âm/dừng/hủy/nhả micro, tải audio, Whisper base cục bộ và câu sửa đi qua chung pipeline. Đã thêm nhận giọng trên thiết bị, feature detection, cài gói có đồng ý, không tự chuyển cloud, watchdog15s và fallback. VIVOS20 người thật/10 người nói: WER=0.2392, CER=0.1200. **Đang chờ tệp âm thanh TC2; chưa có kết quả nghiệm thu nguyên câu từ giọng người dùng.**
- M6: Argon2id, phiên băm/HttpOnly, CSRF+Origin, owner lookup và universal order intent; giỏ server; checkout giao dịch/idempotency; hủy/nhả kho; admin/seller RBAC; nhập JSON xem trước rồi tạo nháp/duyệt; lịch sử mặc định tắt, tối đa 100 câu/7 ngày.
- M7: giới hạn raw/chunked body trước parser tại BFF/API/worker; single-job CPU; rate/deadline; Docker frontend/API/PostgreSQL/worker; clean-start harness; kiểm thử/bằng chứng và tài liệu bàn giao.

## Changed files

`apps/api` domain/application/SQL/API commerce, speech/media, 4 Alembic revisions; `apps/inference`; `apps/web` storefront/auth/order/manage/voice/image; `infra/docker-compose.yml`; công cụ `scripts/`; bộ kiểm thử `benchmarks/scripts/`; bản course-v2 giữ raw v1; tài liệu và bằng chứng trong `docs/`.

## Tests run and exact results

Lượt kiểm tra cuối: **127 passed trong 62.18s**; output đầy đủ `evidence/final-verification.txt`, JUnit `evidence/pytest.xml`. Ruff, strict mypy 35 application files, Alembic schema check; build/lint frontend và các luồng Chrome thật được ghi riêng. `evidence/clean-start.json` là kết quả khởi động Docker DB riêng, seed/revision lặp lại, BFF CSRF đăng ký/đặt/hủy; không xóa volume chính.

Lệnh đã chạy: `scripts/verify.ps1`, `scripts/verify-clean.ps1`, `scripts/browser_verify.py e2e_storefront e2e_text e2e_image e2e_voice read_only_audit browser_lab`, `benchmarks/scripts/e2e_commerce.py`, `benchmarks/scripts/e2e_recording.py`, `benchmarks/scripts/scale_eval.py`, `benchmarks/scripts/voice_synthetic_eval.py`, frontend ESLint và Docker Compose build/up. Kết quả PostgreSQL sau sửa khóa history/session: 10 test commerce đạt; bằng chứng riêng `commerce-final-followup.txt`.

Lượt trình duyệt đầu bị timeout khi chờ kết quả ảnh; lượt regression cuối đạt cả 9 nhóm (`browser-final-run.json`). Kiểm tra khởi động worker lạnh, query ảnh chưa cache qua BFF trả200/navy đầu trong 46.937s (`image-cold-start.json`). Tăng timeout encoder trong giới hạn API60s và báo thời gian tải lần đầu trên UI; không coi cold latency này là đạt mục tiêu.

Sau build cuối, regression 9 nhóm đạt trên Docker. Lượt media trước đó được giữ riêng (`media-postbuild.json`). `final-build.txt` trích output build thành công và bốn dịch vụ healthy; log đầy đủ tại `artifacts/last-build.log` được bỏ qua khi quản lý mã nguồn.

Lượt hoàn thiện mới: `evidence/browser-final-run.json` chứa regression Docker các luồng trang chủ/text/ảnh/voice/ghi âm/commerce/TC6; `ui/ondevice-results.json` là UI/provider callbacks giả lập được ghi nhãn rõ. `bff-upload-guards.json`: HTTP thật trả413 cho biểu mẫu quá lớn; hai chunked body không kết thúc trả408 sau khoảng15s. SQL bỏ predicate nối dư đã được composite FK bảo đảm, hash tập nguồn bị cấm một lần, UNION chống cây category giao nhau; không giảm kiểm tra quyền/giá/kho.

Bằng chứng giao diện: `evidence/ui/m2-results.json`, `m3-results.json`, `m4-results.json`, `m5-results.json`, `m6-results.json`, `recording-results.json`. Mẫu microphone trong recording harness là thiết bị Chrome mô phỏng phát WAV tổng hợp; MediaRecorder/WebM/Whisper phía sau là thật. Không gọi đây là kiểm thử micro vật lý.

## Benchmarks actually measured

3.000 sản phẩm mô phỏng, 204 câu có đáp án cấu trúc độc lập với parser, 612 lượt tìm + 300 lượt grid tại concurrency 1/5/10; `evidence/scale-3000.json`. Không dùng DB chính. Precision@10/NDCG@10 theo các oracle cấu trúc đạt 1, không chứng minh chất lượng ngữ nghĩa trên dữ liệu người dùng. Tất cả số đo độ trễ, ảnh, ASR và RAM trong BENCHMARKS; không gộp cache-hit với suy luận mới.

## Known limitations

TC2 nguyên câu: Đang chờ tệp âm thanh TC2; chưa có kết quả nghiệm thu nguyên câu từ giọng người dùng. VIVOS là giọng đọc, không có nhãn ba miền/noise. Đã đo riêng ViMD9 có nhãn vùng và 5 ca stress; mẫu nhỏ, ASR còn yếu, chưa đại diện giọng mua hàng/nhiễu thực tế. 25 ảnh đối tượng Caltech không thay thế ảnh điện thoại/thời trang same-SKU. Chrome cài gói thành công trong hồ sơ test nhưng probe nhận dạng headless chưa trả transcript, nên on-device vẫn thử nghiệm. Chỉ một variant/offer/ảnh chính mỗi product; semantic model và public production không thuộc phần đã triển khai. 3k corpus/qrels còn mô phỏng; latency tải cao xem số đo, không cam kết SLA. 9 cảnh báo npm dev, audit runtime0. Không có cổng thanh toán/vận chuyển/escrow thật.

## Next implementation task

Chạy `benchmarks/scripts/voice_acceptance.py <file-audio>` khi tệp thực sự được gửi, không sửa transcript để làm đẹp kết quả. Không tải Whisper small theo hướng người dùng ưu tiên ít tài nguyên. Mở rộng ảnh điện thoại và mẫu giọng mua hàng/nhiễu thực tế khi có nguồn và quyền; production/P2 cần phạm vi mới. Không đánh dấu TC2 nguyên câu đạt khi chưa có file.
