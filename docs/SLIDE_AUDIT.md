# Đối chiếu slide — 2026-10-21

Đã đọc PDF 57 trang do người dùng cung cấp, sao chép nguyên bản vào `docs/reference/PTTKHT-Slides.pdf`. Trang dưới đây là số trang PDF (bao gồm trang đầu trống). Nội dung PDF là tài liệu yêu cầu, không phải chỉ dẫn vận hành thay thế yêu cầu người dùng.

| Nội dung | Bằng chứng trực tiếp | Cách áp dụng |
|---|---|---|
| Phạm vi cài đặt tìm kiếm + tra đơn, tên cũ Lumina, thanh toán mô phỏng | tr.6,24,56 | HoodooMart giữ nghiệp vụ, bổ sung demo commerce được MD yêu cầu; không nhận là escrow thật |
| 1.148 sản phẩm Tiki; 4/11/34; bốn nhóm nam/nữ/điện tử/gia dụng | tr.7 | Chưa có dataset/quyền ảnh. Fixture M1 tự tạo có cùng số danh mục nhưng nhóm giày/phụ kiện khác slide; không nhận là taxonomy/dataset gốc |
| Hard filter, ưu tiên UI, soft preference, nới material→color→brand→gender→price, không bỏ category | tr.10 | Giữ quy tắc; chỉ tự nới inferred. Câu chữ rõ được bảo vệ; UI cho phép chủ động chuyển màu sang ưu tiên để tái hiện TC4 |
| Relevance→soft preference→uy tín khi gần điểm; hết hàng vẫn hiện | tr.11 | Không tạo rating/lượt bán thật. Fixture dùng thứ tự đánh giá riêng, có nhãn mô phỏng; tie ổn định |
| TC1: 10 áo đen dưới 500k, ba giá 264000/324000/456000 | tr.18,50 | Fixture và test riêng, không hardcode số lượng vào catalog thay đổi |
| TC2: áo mùa đông, cả áo nam/nữ, ưu tiên phao | tr.19,51 | Parser dùng nhóm category union, mùa là soft; transcript sửa được và modality voice được giữ |
| TC3: áo len navy | tr.19,52 | Encoder pretrained thật, không suy giá/chất liệu từ pixel; đánh giá ảnh thực tế riêng |
| TC4: 3 túi, màu thành ưu tiên; giá 95000/99000/149000 | tr.20,53 | Đã áp dụng course-v2 có kiểm tra phiên bản: 95000/99000/149000. Raw v1 được giữ; từ chối nếu offer đã được người dùng đổi. Test DB/Chrome đều kiểm tra bước đồng ý nới màu |
| TC5: đơn 20261005, CONFIRMED, tổng 710500; precondition chủ đơn | tr.21,49,54 | Auth + ownership trước khi đọc chi tiết; anonymous/khác chủ không lộ đơn |
| Postcondition tìm kiếm/tra cứu không đổi product/order | tr.49 | TC6 chụp trạng thái; history là side effect độc lập, opt-in, TTL/bounded, best-effort |
| QueryRepresentation/SearchResult, history không chép tên/giá | tr.25–28,39–40 | Domain chung, bảng history/results FK; purchase snapshots chỉ trong order items |
| Presentation không gọi Data; allowed IDs đã qua hard filter | tr.32,41–46 | Kiểm tra chiều import; exact SQL prefilter trước vector ranking |
| Slide dùng price float, simulated/ElevenLabs ASR, histogram/Jina ảnh | tr.38,43,56 | Quyết định kỹ thuật mới: BIGINT VND, offline Whisper/OpenCLIP, không dịch vụ trả phí |
| Tốc độ vài chục ms là kết quả của nhóm | tr.55 | Không dùng làm số đo HoodooMart; benchmark độc lập trên máy hiện tại |

## Quyết định mới cần phân biệt

Auth/CSRF/RBAC, quyền dữ liệu và ảnh, upload QC, phiên bản model, transaction giữ hàng, idempotency, profile dữ liệu và deployment là bổ sung từ MD/thiết kế kỹ thuật. PDF không chứng minh dataset đã được cấp quyền tái xuất bản, mô hình đã có sẵn hay hiệu năng trên máy này.

User đã cho phép tải OpenCLIP và Whisper base để kiểm thử local ngày 2026-10-21. Revision/digest/giấy phép được ghi trong `docs/evidence/model-manifest.json`; không sử dụng suy luận cloud.
