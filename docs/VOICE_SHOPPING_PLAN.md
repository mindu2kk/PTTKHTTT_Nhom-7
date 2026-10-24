# Chất lượng tìm hàng bằng giọng nói — mục tiêu 70%

## Tiêu chí được người dùng xác nhận

Ít nhất 70% câu nói tìm đúng ý và sản phẩm, gồm giá, màu và danh mục. Đơn vị
là **câu**, không phải phần trăm từ đúng hay mức giảm WER.

Một câu thành công cần đồng thời: giữ toàn bộ điều kiện bắt buộc trong đáp án,
không trả sản phẩm vi phạm điều kiện, và có sản phẩm liên quan trong top5. Câu
catalog không có hàng phải trả rỗng đúng lý do; báo riêng nhóm này. Không tự nới
giá/màu/danh mục hoặc coi lời gợi ý đã được người dùng xác nhận.

## Thực hiện

1. Khôi phục stack local, giữ DB và đơn hàng hiện có.
2. Khóa 100 câu text mua sắm với đáp án dựa trên catalog công khai, đo baseline
   trước sửa. Đây là bộ phát triển/hiệu chỉnh sau khi đã xem lỗi, không gọi kết
   quả chạy lại là đánh giá mù độc lập.
3. Sửa các lỗi được tái hiện ở parser và xếp hạng; thêm unit và hồi quy integration.
   Agent phụ trách oracle, audit parser và nghiên cứu ASR theo các phạm vi riêng.
4. Cung cấp công cụ thu âm local tự nguyện; khóa đáp án trước audio/ASR. Audio
   giọng đọc tin tức VIVOS/ViMD và giọng tổng hợp không thay thế câu mua hàng thật.
5. Chấm first-pass và assisted riêng. Không có đủ audio hợp lệ thì gate voice là
   chưa đánh giá, dù kiểm text đạt. Mẫu thiếu/lỗi/timeout không được bỏ khỏi mẫu số.
6. Ghi lệnh, kết quả, độ trễ và giới hạn trong báo cáo mới, giữ nguyên bằng chứng
   M7/M8 và nâng cấp ASR trước đó.

## Giới hạn

Giữ PhoWhisper-base int8 hiện có, LOCAL_ONLY=true, không API trả phí, không tải
trọng số mới, không nhập thêm dữ liệu ngoài hoặc thay schema. Vocabulary công khai
chỉ cung cấp gợi ý sau ASR; không mô tả thành mô hình đã hiểu mọi ngữ cảnh mua sắm.
Giá/kho của real_demo là mô phỏng. Không có sản phẩm phù hợp thì không bịa kết quả.
