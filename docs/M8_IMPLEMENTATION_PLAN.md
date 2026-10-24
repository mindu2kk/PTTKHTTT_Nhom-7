# M8 — kế hoạch thực hiện

Phạm vi: nâng cấp tăng dần, giữ kiến trúc Next.js → BFF → FastAPI → PostgreSQL và worker CPU. Không sửa báo cáo nghiệm thu M7; TC2 vẫn chờ tệp thật.

1. **P0:** baseline regression, kiểm quyền ba nguồn được gợi ý và ABO chính thức; staging có hash/revision, nhập mẫu rồi cohort 300–500 sản phẩm, ảnh thật đúng ID; chỉ mục offline tăng dần.
2. **P1:** token cam đỏ, header tìm kiếm chung, trang chủ marketplace, thẻ ảnh thật, danh sách/bộ lọc URL và trang chi tiết/gallery.
3. **P2:** giữ text/voice/image pipeline; giỏ và checkout mô phỏng; kiểm responsive 360/390/768/1280/1440 và accessibility.
4. **P3:** regression đầy đủ, benchmark mới theo catalog thực, kiểm mapping/index/quyền, tài liệu và ảnh chụp.

## Quyết định dữ liệu

- ABO (Amazon.com, CC BY 4.0 bao gồm ảnh) là nguồn chính được duyệt qua README/LICENSE và AWS Open Data Registry ngày 2026-10-22. Chỉ tải metadata và ảnh được chọn, không tải kho ảnh nhiều GB hoặc trọng số mới.
- Hồ sơ `real_demo` tách sản phẩm/ảnh thật khỏi `demo_seed` bài học. Offer và hạn mức đặt thử là cấu hình mô phỏng riêng, không giá bán/tồn kho thương nhân, không chuyển đổi giá nguồn. Hiển thị rõ trong UI.
- Giữ dữ liệu M7; không archive/xóa sản phẩm cũ để thay catalog. Không thay đổi cây cũ; thêm nhánh điện tử/gia dụng nếu cần và ghi số thực tế.
- Trang có quyền ảnh không rõ không được publish. Không lấy URL công khai làm giấy phép.

## Gate

Nhập lặp không trùng/ghi đè dữ liệu người dùng; mapping hash/ID đúng; catalog public chỉ ảnh được duyệt; tất cả ảnh public có vector tương thích; parser/quyền/order/checkout regression đạt; UI không overflow và hành động thật. Đo mới thay vì dùng số M7. Mọi số thiếu/giới hạn giữ nguyên trong completion audit.

## Kết quả chốt

318 sản phẩm public sau QC, 624 ảnh/624 vector, replay không tạo mới; 151 backend tests và 8 nhóm browser đạt. Mục tiêu cohort 300–500 đạt; 1000/3000 thật chưa triển khai/đo. Xem M8_COMPLETION_AUDIT và M8_TEST_REPORT.
