# M8 — giao diện marketplace

## Hướng thiết kế

Thương hiệu HoodooMart độc lập. Tham khảo phân cấp tìm kiếm/danh mục/grid thường gặp ở marketplace Việt Nam theo brief. Truy cập trực tiếp `https://shopee.vn/` bằng web tool bị timeout; không tuyên bố đã kiểm mọi chi tiết live của Shopee, không vượt chặn hoặc lấy tài sản của họ.

Token ở `apps/web/src/app/marketplace.css`: primary đất nung `#b6381d`, nền `#f5f5f3`, surface trắng, hero kem `#fff1df`; chữ Segoe UI/Arial hỗ trợ tiếng Việt, radius4–10px, border nhẹ. Tái dùng Tailwind4, shadcn Button/Sheet/Dialog/Skeleton/Alert hiện có và Lucide. Không thêm UI library/font từ xa.

## Trang và hành vi

- Header sticky: tiện ích có route thật, tìm kiếm GET cùng suggestions API, microphone/camera mở công cụ thật, giỏ đếm theo trạng thái hiện tại và aria-live. ID input riêng theo instance.
- Home: hero nguyên bản dùng ảnh của sản phẩm API, danh mục API, gợi ý/mới trong catalog từ DB. Không bán chạy/rating/countdown/discount giả.
- `/products`: sidebar desktop, Sheet mobile có focus trap/title/close; filter URL, category/subcategory/giá/brand/màu/chất liệu/giới tính/phiên bản và khả năng đặt thử; sorting thật, pagination, empty state.
- `/products/[slug]`: gallery chính/ảnh thu nhỏ, Dialog phóng to, tên gốc/nhãn hiệu/màu/chất liệu nguồn, giá và hạn mức đặt thử có nhãn; quantity, thêm giỏ, đặt thử ngay; related cùng category API. Chỉ phiên bản thực trong source, không tạo size giả.
- `/search`, `/search/voice`, `/search/image`: giữ pipeline M7; text/voice/image cùng bộ lọc và ProductCard. Voice cho sửa transcript, image có drop/preview/validation/loading; không tuyên bố TC2 đạt.
- Cart/checkout/order: thumbnail đúng product, quantity/remove/subtotal, revalidation/atomic reservation/idempotency/ownership giữ nguyên. COD/mock được ghi rõ; không nhận thẻ hoặc giao hàng thật.
- `/sources`, `/help`: attribution, giới hạn, giải thích đặt thử và quyền riêng tư. Không có nút notification/wishlist/tracking carrier giả.

## Hiệu năng và khả năng tiếp cận

SSR cho dữ liệu/price/action; chỉ state tương tác ở client. Next Image dùng derivative WebP tạo trước320/960, không cần chạy Sharp lặp khi request. Ảnh dưới fold lazy; tỷ lệ ảnh cố định tránh CLS, fallback ảnh hỏng có nhãn. Skeleton cho tải route, focus-visible, label cho input/icon, Escape/return focus trong overlay, reduced motion. Các số LCP/CLS/INP lab và screenshot thực tế ghi trong TEST_REPORT, không suy ra field performance từ CSS.

Kiểm tại360/390/768/1280/1440. Những thiếu sót phát hiện khi nhìn screenshot được sửa trước bàn giao; screenshot đầu pilot không phải ảnh cuối nghiệm thu.

Kênh quản lý real_demo chỉ đọc và có thông báo rõ, không hiện nút tạo/sửa/duyệt không được hỗ trợ. Giao diện nguồn demo_seed M6 vẫn dùng riêng. Skeleton được đặt ở listing page, không ở root, để trang sản phẩm không tồn tại giữ đúng HTTP404.
