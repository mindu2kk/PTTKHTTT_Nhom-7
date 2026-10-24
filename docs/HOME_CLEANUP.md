# Thu gọn trang chủ — 2026-10-23

Theo ảnh người dùng: bỏ toàn bộ hero khẩu hiệu, hai thẻ giới thiệu AI/ảnh, hàng công cụ đóng khung, bốn thẻ danh mục nhiều chữ và dải tìm ảnh lặp. Thay bằng một banner minh họa không chữ, hàng danh mục không khung và một lưới24 sản phẩm. Bỏ eyebrow/tab/bộ sưu tập chia lặp; giảm chiều cao header, bỏ thông báo thử nghiệm trên đầu (nhãn Giá đặt thử trên thẻ và thông tin footer/checkout vẫn có).

Ảnh mới tạo bằng **built-in image_gen**, lưu trong dự án: `apps/web/public/images/campaign/hoodoomart-still-life-v1.png`. Next Image xuất kích thước phù hợp và tối ưu WebP qua cache có sẵn. Chỉ là campaign art, không ánh xạ vào SKU/catalog/gallery/vector. Ghi nguồn ảnh minh họa ở trang Nguồn dữ liệu. Không đổi backend, model, giá/kho/đơn hoặc dữ liệu catalog.

Prompt dùng để tạo ảnh:

> Create a finished original panoramic ecommerce homepage banner for HoodooMart, inspired by the cheerful energy of Vietnamese shopping campaign art, not any existing company's assets. Pure visual art: absolutely no text, lettering, numbers, logos, badges, discount claims, UI buttons, panels, cards, or borders. Very wide 3.3:1 panoramic composition, ideally around 1800 by 550. A polished playful studio still-life: one pair of stylish unbranded ivory and terracotta sneakers, smooth silver over-ear headphones, a small terracotta desk lamp, and a folded soft textile arranged on clean low display platforms. Large objects fill the frame elegantly, realistic premium materials, clean edges, bright warm light, soft natural shadows. Rich vibrant vermilion orange background with cream highlights, small light cyan accents and subtle diagonal paper sweep, strong visual hierarchy, minimal props, airy negative space around the objects, sophisticated editorial product photography with a touch of 3D campaign art. Objects are generic decorative campaign illustrations, no brand markings. Keep the meaningful arrangement in the central 80% so responsive cropping works. No written marketing copy whatsoever.

Tệp sửa: page.tsx, layout.tsx, sources/page.tsx, marketplace-ai.css, marketplace-banner.tsx, site-header.tsx. Cập nhật selector tiêu đề trong harness m8_browser để tương thích tên mục mới, giữ nguyên báo cáo lịch sử. Build/lint và kiểm Chrome responsive ghi riêng trong `evidence/home-cleanup`; không chạy lại backend tests cho thay đổi bố cục này.

## Kết quả kiểm tra

Build Docker, ESLint và TypeScript đạt. Chrome thật ở360/390/768/1280/1440: không tràn ngang, banner và ảnh sản phẩm tải đủ,24 thẻ sản phẩm, không có input/textarea trong nội dung trang chủ, điều hướng danh mục hoạt động. Lượt kiểm đầu chờ URL chưa đủ cho client navigation; đã đổi sang chờ URL thực tế rồi chạy lại đạt. Bằng chứng: evidence/home-cleanup/browser.json và home-*.png. Không chạy lại tests AI/backend vì không sửa nghiệp vụ.

Provenance/hash ảnh: data/sources/storefront-art.json. Ảnh sinh bằng built-in image_gen; runtime website chỉ phục vụ tệp cục bộ và vẫn LOCAL_ONLY=true.
