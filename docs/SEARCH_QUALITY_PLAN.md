# Kiểm thử và sửa chất lượng search — 2026-10-23

1. Viết oracle độc lập cho parser/ranking/filter/ảnh/speech; chạy unit không DB, HTTP hoặc weights. Chạy test tái hiện trước khi sửa và giữ log lỗi.
2. Sửa từ gần âm có dấu, giá nói bằng chữ, chiều bất đẳng thức và khoảng giá. UI filters luôn ưu tiên; không nới bộ lọc hoặc sửa số tiền theo fuzzy matching.
3. Giữ câu voice gốc. Chỉ đưa gợi ý ở các cụm sản phẩm có bảng nhầm hữu hạn; người dùng phải chọn và bấm tìm. Hiển thị cảnh báo recognizer đã trả thay vì bỏ qua.
4. Đo ASR baseline và thử decoder context/beam trên đúng audio có sẵn, không tải model/dataset, không dùng cloud. Không đưa cấu hình gây regression vào bản chạy.
5. Chạy frontend unit, integration trên DB test riêng, static/build và Chrome; tách test giả lập khỏi chất lượng nhận giọng thật. Giữ báo cáo cũ M7/M8.

Theo FastAPI/storefront skills: giữ router → application → domain ports, bộ lọc phía server và named controls của Dialog hiện tại. Kết quả/phạm vi tại [SEARCH_QUALITY_REPORT](SEARCH_QUALITY_REPORT.md).
