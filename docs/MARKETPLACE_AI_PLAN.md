# Marketplace và AI — 2026-10-23

## Tham khảo và phạm vi

Browser mở https://shopee.vn/ và đọc được cấu trúc trang chủ: utility bar, tìm kiếm trung tâm, giỏ, banner chính/kề, lối tắt, lưới danh mục và các bộ sưu tập. Sau đó màn hình xuất hiện CAPTCHA; không vượt chặn, chưa kiểm được listing/PDP hay backend nội bộ Shopee. Backend dưới đây là thiết kế của HoodooMart, không suy ra công nghệ Shopee từ giao diện. Không sao chép thương hiệu, khuyến mại hay số bán/đánh giá.

## Thiết kế

Giữ token hiện có: primary #b6381d, accent #cf4729, cream #fff1df, nền #f5f5f3, chữ #272723, surface trắng; Segoe UI. Bố cục 1240px, căn trái; header tìm kiếm trung tâm, banner lớn + hai ô bên cạnh, danh mục ảnh thật, sản phẩm sáu cột/hai cột mobile. Điểm nhấn duy nhất là banner sản phẩm; các vùng còn lại dùng đường viền mảnh và khoảng cách gọn. Thay hero khẩu hiệu lớn bằng bộ sưu tập có nội dung/ảnh từ catalog và lối tắt chức năng thật.

```text
utility | logo — search — account/cart
category menu | roots | AI | image | voice
main collection image/banner       | image search
                                   | shopping assistant
quick actions / image category grid
discovery products | new catalog products
```

## Triển khai

1. Storefront/frontend-design: trang chủ gọn, điều hướng danh mục desktop/mobile dùng Sheet hiện có; footer liên kết thật. Giữ SSR và ảnh WebP/thumb có sẵn.
2. FastAPI/application/domain ports: dịch vụ hỗ trợ chọn sản phẩm có context bộ lọc phía client, so sánh tối đa3 ID qua public catalog, không truy cập đơn hoặc tạo giao dịch. Không lưu hội thoại/raw media.
3. Tìm mô tả hình ảnh: dùng text tower OpenCLIP ViT-B/32 đã được duyệt, mapping khái niệm Việt sang prompt tiếng Anh hữu hạn; không nhận là mô hình ngôn ngữ tiếng Việt hay chatbot sinh nội dung. Giá/danh mục/màu vẫn lọc cứng trước cosine; từ không hiểu yêu cầu làm rõ, không trả đại sản phẩm. Voice/ảnh giữ đường xử lý thật.
4. Test DB riêng; baseline/regression, case filter/unknown/order/rights/compare, suy luận CPU thật, Chrome responsive/keyboard/negative uploads. Báo cáo đo mới riêng, không thay số M8/M7.

Giữ LOCAL_ONLY=true, không tải mô hình mới/API trả phí. TC2 thiếu audio người dùng vẫn ghi chờ; giá/hạn mức đặt thử mô phỏng. Không thêm payment/carrier, sales/reviews giả hoặc thu thập dữ liệu Shopee.
