# Kiến trúc hiện tại

Modular monolith: Next.js → same-origin BFF → FastAPI → PostgreSQL; một worker CPU riêng cho OpenCLIP/Whisper. Không có API suy luận từ xa, Redis hay GPU bắt buộc.

## Phân lớp

`api/v1 → application → domain`; infrastructure triển khai ports; `core/dependencies.py` ghép dịch vụ. Test AST chặn router nhập SQL repository và domain/application nhập framework/infrastructure. Query/Commerce/Media ports có thể thay provider.

## Tìm kiếm chung

UI thường dùng một `UnifiedSearch` trong layout, key theo pathname/query của trang nền. Ô search phát thao tác text/voice/image tới cùng controller; Dialog giữ URL hiện tại và kết quả tạm trong RAM. Voice click mới xin micro, MediaRecorder tự dừng12s, stop tự gọi `/search/voice`, người dùng sửa câu rồi gọi `/search/text` với modality voice. Ảnh lấy từ picker/drop/ClipboardEvent có bytes, không fetch URL clipboard; text/ảnh dùng cùng bộ lọc. Close/cancel/unmount/tab ẩn dừng tracks/timer, abort HTTP và tăng epoch để bỏ kết quả đến trễ. Cache/suy luận server vẫn chịu gate/deadline, không tuyên bố abort client giết được tác vụ CPU đang chạy.

Text hoặc transcript đã sửa → NFC/accent shadow/aliases/prices → QueryRepresentation (origin/operator/confidence) → SQL lọc quyền, publication, category subtree, giá/thuộc tính → lexical hoặc allowed-ID exact cosine → ranking ổn định → phân trang. Category/UI không nới; explicit text chỉ nới sau đồng ý. Giới hạn 1000 candidate, có thông báo khi chạm trần. Tìm chính dùng lexical; trợ lý mô tả bổ sung text tower OpenCLIP đối chiếu ảnh như phần dưới.

Ảnh: validate nội dung/MIME/extension/5MB/12MP → RGB/re-encode bỏ metadata → encode512D đúng revision → pgvector chỉ trong candidate đã lọc và đúng hash/revision. Vectors gallery tạo offline; cache5 phút/max100 chỉ chứa vector query, không chứa tệp gốc. Revalidate giá/kho hiện tại mỗi lần tìm.

Giọng: ghi tối đa12s ở browser, server nhận≤15s/2MB; PyAV decode mono16k trong worker; Whisper base int8 vi; trả metadata/warnings → sửa câu → cùng search service với modality voice. Không tự tìm ngay khi nhận xong bản chép lời. Ghi âm/hủy/navigation đóng tracks và ObjectURL.

## Auth và giao dịch

- Argon2id qua bounded threads; token phiên ngẫu nhiên, chỉ SHA256 trong DB, expiry7d, cookie HttpOnly/SameSite Lax. CSRF double-submit + Origin allowlist cho ghi nghiệp vụ; BFF kiểm origin. Secure cookie bật khi dùng HTTPS; mặc định loopback HTTP.
- Owner lookup luôn `orders.user_id=actor.id`, mã không tồn tại và người khác cùng404. Order intent không rơi sang product search sau thất bại. Không có admin mặc định; cấp role/gán order mẫu qua CLI nhập mật khẩu ẩn.
- Giỏ server không giữ kho. Checkout khóa user để serialize idempotency; khóa offer/inventory theo thứ tự ID; kiểm lại public/price/stock, ghi order/items/reservations/mock payment/shipment trong một transaction. Khác body cùng key →409.
- Hủy trước SHIPPED nhả held một lần. SHIPPED trừ on_hand và reserved, chuyển consumed; status progression có gate. Không có thanh toán/escrow thật.
- Seller chỉ sửa draft/offer mình; thay đổi seller cần duyệt lại; admin duyệt quyền/ảnh trước publish. Import JSON≤20 bản, xem trước kiểm category/image; nhập thành nháp; lặp exact body tái dùng raw hash trong cùng nguồn operator. Một batch provenance cho mỗi bản ghi.

## Dữ liệu và vận hành

25 bảng trong DATA_DICTIONARY, revision head `0005_real_catalog`. [ERD lịch sử M7](diagrams/catalog-erd.svg), [nguồn Mermaid M7](diagrams/catalog-erd.mmd) ghi schema trước mở rộng gallery; schema hiện tại theo DATA_DICTIONARY và migration0005. Một variant/offer mỗi product; nhiều ảnh gallery, một primary qua partial UNIQUE; không gọi đây là marketplace multi-seller đầy đủ.

History mặc định tắt, chỉ text/transcript sau tìm; background task best-effort ngoài response, max100/user. API đọc lọc/purge7 ngày; maintenance giờ xóa quá hạn và sessions. Không lưu raw audio/image, không log bodies/querystrings/secrets. Search không ghi bảng nghiệp vụ.

Raw/chunked body có bound trước multipart ở BFF/API/worker; SQL3s, request5s hoặc60s media; inference một job, busy429; giới hạn tốc độ theo process local. Docker ports chỉ127.0.0.1; frontend/API/inference non-root; web read-only filesystem/cache tmpfs. Current DB role là owner phát triển; xem SECURITY cho giới hạn production.

P2 payment/carrier/finance/dispute chỉ có domain Protocol trong `domain/integrations.py`; chưa có live adapter.

## M8: catalog ảnh thật

Hồ sơ real_demo tách khỏi demo_seed; metadata/ảnh ABO được duyệt CC-BY4, offer và hạn mức đặt thử mô phỏng riêng. Ảnh WebP960/320 từ staging có ID/hash/provenance, mount read-only, không lưu uploads vào catalog. Chỉ mục offline tăng dần, cosine aggregate theo product cho nhiều ảnh; luôn kiểm quyền và revision/hash. Kênh quản lý real_demo là read-only có thông báo; nhập mới qua pipeline review. Xem M8_IMPLEMENTATION_PLAN/M8_IMAGE_PIPELINE/M8_SEARCH_REINDEX. Các báo cáo M7 là lịch sử riêng.

## Hoàn thiện marketplace/AI, 2026-10-23

`/search/describe` → ShoppingAssistant → domain LocalTextEncoder/ImageVectorIndex → HttpTextEncoder và cùng SqlImageVectorIndex. Mô tả Việt được map qua từ vựng hữu hạn, encode bằng text tower của đúng OpenCLIP đã có; gallery512D/revision/hash giữ nguyên nên không tạo lại index. Lọc quyền/publication/category/giá/màu trước cosine; riêng mô tả dùng cosine chính xác hơn thay band làm tròn để tránh ID quyết định các điểm gần nhau. Nhánh ảnh M8 giữ band cũ. Worker image/text dùng chung model và semaphore, cache tối đa100 vector/5 phút, không raw text. Tác vụ CPU một lượt; API deadline60s cho mô tả như ảnh/giọng.

`/search/compare` đọc lại tối đa3 sản phẩm công khai qua CatalogRepository, không truy cập đơn/kho riêng hay tạo giao dịch; ID không public trả404 chung. UI giữ snapshot bộ lọc để phân trang, không lưu hội thoại. Các công cụ này không có adapter suy luận cloud hoặc weights mới. Xem MARKETPLACE_AI_REPORT cho số đo/giới hạn.
