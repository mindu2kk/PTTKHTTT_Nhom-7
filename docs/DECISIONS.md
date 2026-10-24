# Quyết định đang áp dụng

1. PDF đã đọc trực tiếp, 57 trang; nguồn và số trang tại SLIDE_AUDIT. Tên HoodooMart là thay đổi thương hiệu; không tự thay nghiệp vụ slide.
2. Giữ fixture CC0 gốc 4/11/34, không tự nhận tên cây/dataset Tiki gốc. Course-v2 là bản hiệu chỉnh hai giá riêng, có old-revision guard; không sửa raw v1/không ghi đè offer đã được người dùng đổi.
3. Category và UI-selected luôn hard; explicit text chỉ nới khi có đồng ý. TC4 thêm bước consent, công bố khác slide auto-relax.
4. Lexical/rule text baseline được chọn để giữ CPU/chi phí đơn giản; không gọi nó là AI hay semantic/hybrid. Giới hạn1000 candidate được thông báo. Không thêm GIN/HNSW khi chưa có plan/recall chứng minh cần.
5. OpenCLIP và Whisper base được tải sau consent, pinned revisions/digests/MIT; một CPU worker, một job chung. Không model trong mỗi API worker, không paid/vendor speech API.
6. Whisper base chạy thật nhưng không được tuyên bố đạt chất lượng từ mẫu TTS. Repetition guard và bản chép lời sửa được là cơ chế bảo vệ, không phải thay thế đánh giá giọng người thật. Tin nhắn câu TC2 của người dùng nhận được dưới dạng text, không có audio waveform để chấm ASR.
7. Auth opaque server session/hash/Argon2 thay vì JWT dài hạn; CSRF+Origin và private owner filtering. Admin/seller chỉ cấp bằng local CLI, không default public credential.
8. Checkout mock/COD, row locks và idempotency; không card/escrow thật. Reserve ở checkout, không ở cart/search. Chỉ consume khi ship, cancel trước ship nhả một lần.
9. History opt-in false, max100/7d; ghi background best-effort. Opt-out và history writer khóa cùng user để không để lại bản ghi sau khi tắt; hourly physical purge.
10. Cookie chứa guest IDs/qty; giỏ lớn vượt ngưỡng cookie dùng localStorage có marker. Logout xóa dữ liệu guest; server vẫn kiểm toàn bộ giá/kho/quyền. Không raw media trong cookie/history.
11. Full CPU Compose là cách chạy chính. Native frontend cần Node24; image Node24.13.0, API Python3.12.12; native Python3.13 là môi trường phát triển phụ. Chỉ bind loopback, chưa public deployment.
12. shadcn CLI thuộc dev/build dependency; audit runtime0, full dev9high chưa có upstream patch. Không dùng audit --force để downgrade framework. P2 payment/carrier/finance/dispute chỉ là Protocol, không live adapter.
