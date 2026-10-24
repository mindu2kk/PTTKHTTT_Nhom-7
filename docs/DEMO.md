# Kịch bản demo theo slide

## Chuẩn bị

Chạy quickstart README, course-v2 và `scripts/index_images.py`; tạo tài khoản riêng trong UI. Đơn mẫu `20261005` chỉ xem được sau lệnh local `provision_account.py --email ... --bind-fixture-order`; nhập ẩn mật khẩu, không có tài khoản mặc định. Không gán đơn người khác: CLI chỉ cho order mẫu chưa có chủ.

1. Mở localhost:3000, xem nhãn dữ liệu mô phỏng, danh mục, chi tiết/VND/tồn kho và giỏ.
2. **TC1:** nhập `áo len nam màu đen dưới 500k` →10, giá đầu264000/324000/456000; xem hard chips. Thử `ao len nam den duoi 500 nghin`.
3. **TC2:** vào Giọng nói, cho phép micro và nói `tôi muốn mua áo mùa đông`; xem/nghe bản ghi, bấm chuyển chữ; kiểm tra/sửa câu rồi tìm. Winter là ưu tiên mềm, áo phao đầu. Công bố rõ: Whisper base chưa đạt gate giọng thật; không phát file TTS rồi gọi là người nói thật.
4. **TC3:** tải `benchmarks/images/navy-sweater-heldout.png` vào Hình ảnh →navy sweater cạnh tranh đầu; thử thêm danh mục/giá và reload URL. Đây là minh họa held-out gốc, không ảnh smartphone.
5. **TC4:** nhập `túi đeo chéo màu đỏ dưới 150k` →1. Bấm “Cho phép mở rộng màu” →3, đỏ95000 đầu; hai giá khác99000/149000 theo course-v2. Giải thích bước đồng ý thêm so với slide để bảo vệ điều kiện người dùng.
6. **TC5:** đăng nhập đúng chủ, nhập `kiểm tra đơn hàng 20261005` →order CONFIRMED,115500+595000=710500. Mở bằng tài khoản khác →thông báo chung không tìm thấy, không lộ order.
7. **TC6:** chạy read_only_audit.py và pytest: business-state hashes không đổi khi tìm; lịch sử chỉ lưu riêng khi opt-in. Không dùng việc click search như thao tác reserve.
8. Thêm sweater còn kho →cart→COD/mock checkout→đơn CONFIRMED→hủy. Giá/stock đổi sẽ409 để kiểm tra lại; retry cùng key không tạo đơn trùng.
9. Tài khoản→bật lịch sử→tìm→xem/xóa/tắt. Admin local→quản lý→tạo/nhập JSON nháp→kiểm duyệt→publish. Người bán không tự publish.

## Lỗi có chủ ý cần trình bày

Từ chối micro →nhập text/tải audio; ảnh hỏng/HEIC/oversize →thông báo; model busy/unavailable →thử lại hoặc text; query không liên quan→empty; out-of-stock thấy được nhưng không thêm giỏ. Không bịa rating/sold, carrier/payment live hoặc dữ liệu Tiki.
