# Dữ liệu hiện tại — 27 bảng

Schema do Alembic quản lý, head `0009_product_image_order`; không create_all runtime. VND BIGINT, số lượng integer. PostgreSQL vector/pg_trgm/unaccent được cài qua migration.

| Bảng | Nội dung/khóa và bất biến |
|---|---|
| data_sources | revision/license/rights/allowed_use/check time; demo/approved/unknown/restricted |
| import_batches | source FK, counts/errors/status/time; nháp→duyệt/lưu trữ |
| source_products | PK(source_id,external_id), raw JSON/SHA256/batch; giữ raw v1 khi course-v2 thêm provenance |
| categories | unique slug, self parent FK, level≥0; recursion không giới hạn3 tầng |
| products | unique slug, original/vi text, category/brand/gender, profile/publication/review, search shadow |
| product_sources | composite raw-record FK; mọi nguồn phải có quyền, không chỉ một nguồn tốt |
| product_attributes | PK(product,key), canonical/display/review/provenance/confidence0–100 |
| product_images | product FK có index; partial UNIQUE cho một primary/product, gallery nhiều ảnh, sort_order≥0; storage key index; hash/size/license/alt |
| product_variants | unique product/SKU; size/color/options/status; một variant/product |
| seller_offers | unique product/variant; composite variant/product FK; integer price>0/kind; seller verified+active |
| inventory | offer PK/FK; 0≤reserved≤on_hand; version tăng theo biến động |
| users | email unique, nullable Argon2 hash, active, history_opt_in=false; fixture owner disabled |
| user_roles | PK(user,role), role customer/seller/admin; không nhận role từ form đăng ký |
| seller_profiles | user FK/PK, approved=false; chỉ operator cấp hồ sơ demo được duyệt |
| sessions | SHA256 token PK, user FK, expiry index; raw token chỉ trong cookie |
| carts | user PK/FK, timestamp; không reserve stock |
| product_sizes | INT PK, product FK, UNIQUE(product,size); S/M/L/XL/XXL/F; 0≤reserved≤stock_quantity |
| cart_items | PK(user,product_size), composite product_size/product FK; qty1–99; cart≤50 lines |
| orders | unique code, owner FK, status/total/profile/address/time; unique(owner,idempotency_key), request hash |
| order_items | name/price/size purchase snapshots; product_size/product composite FK; size NULL only for legacy orders |
| stock_reservations | PK(order,offer,product_size), qty>0, held/released/consumed; nhả/consume đúng một lần |
| mock_payments | order PK/FK, cod/mock, pending/simulated_paid/cancelled; không lưu card |
| shipments | order PK/FK, local_demo provider, status mô phỏng |
| search_queries | owner FK/text≤300/modality/time, opt-in, max100, TTL7d+purge tối đa1h |
| search_results | PK(query,product), rank; cascade khi xóa query; không dùng làm sold/rating giả |
| image_embeddings | PK(image,model,revision), 512D vector/content hash/time; không trộn text vectors |

FK đơn hàng/source hạn chế xóa để giữ bằng chứng; sessions/role/history/cart children cascade theo quan hệ đã khai báo. Xóa lịch sử không xóa order hay tồn kho. Migration downgrade trên dữ liệu có storage key trùng/deep category có thể bị chặn bởi UNIQUE/CHECK cũ; không xóa dữ liệu để ép rollback. Backup và xem RUNBOOK trước thao tác schema thật.

M8 bổ sung profile real_demo qua migration0005, giữ nguyên25 bảng. Source metadata/ảnh thật và offer demo tách bằng raw/field provenance/price_kind. Rollback0005 từ chối khi còn real_demo hoặc gallery nhiều ảnh để giữ dữ liệu. Cây public real_demo hiện4/4/19; cây fixture cũ được giữ riêng.

Hiện tại: xem [PRODUCT_SIZES](PRODUCT_SIZES.md) cho migration 0008, kho tổng/kho size và dữ liệu lịch sử.

Migration 0009 thêm product_images.sort_order để giữ thứ tự URL/ảnh bìa khi admin chỉnh gallery; tổng vẫn 27 bảng. Nguồn ảnh URL được xác nhận riêng, không gán giấy phép CC0 của metadata cho ảnh.
