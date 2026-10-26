# Nhập DataShopping cập nhật — 2026-10-26

Đã đọc19 dòng dữ liệu từ sheet đầu của DataShopping.xlsx, bỏ qua sheet ghi chú. Nguồn Rhodi, ảnh trực tiếp Postimages; tiếp tục quyền sử dụng nguồn đã được người dùng xác nhận cho web demo. Không sửa file Excel, không tải ảnh vào thư mục project.

## Kết quả

-18 sản phẩm mới; tái sử dụng rhodi-p11847; catalog public real_demo hiện19 sản phẩm/19 ảnh.
- Sản phẩm cũ vẫn on_hand8/reserved1, không reset giỏ/đơn/kho đang giữ.
-18 dòng thiếu kho được cấp hạn mức demo ngẫu nhiên5–20 theo yêu cầu người dùng. Giá trị được tạo một lần trong artifacts/shopping-updated-import.json và lưu DB; không ngẫu nhiên lại theo request.
- Tên/mô tả/giá/màu/size và danh mục theo sheet. Danh mục map chính xác vào19 ID lá hiện có. Giữ phân loại Nhẫn theo cột danh mục người dùng cung cấp, không tự đổi taxonomy.
- Phụ kiện thiếu size và kính thiếu màu hiển thị Chưa có thông tin, không tự coi là Freesize hoặc bịa màu.
- Danh sách size/màu được giữ ở trường hiển thị và ProductVariant.option_values.available_sizes/available_colors. Hiện vẫn một biến thể tổng hợp cho mỗi sản phẩm; CHƯA tách SKU hay kho theo size/màu và CHƯA làm luồng chọn từng biến thể. Không coi chuỗi nhiều size là một kích thước vật lý.
- Không khẳng định kho/giá đang bán live của Rhodi. Không tạo thêm đánh giá/doanh số/AI index.

## Cách nhập và bảo vệ dữ liệu

CLI app.infrastructure.shop_sample nhận một object hoặc list JSON từ stdin, có --rights-reviewed. Thêm --dry-run để chạy mọi kiểm tra rồi rollback. Mọi dòng nhập chung một transaction; lỗi một dòng rollback toàn bộ. Kiểm source ID trùng trước nhập; cùng raw_hash tái sử dụng, raw drift bị từ chối, không ghi đè dữ liệu đã thay đổi. option_values giữ danh sách đầy đủ, giá/kho là số nguyên VND/số lượng.

Ảnh được kiểm tra nội dung/hash/kích thước trong RAM tối đa3 lượt đồng thời, cố định host HTTPS i.postimg.cc, không redirect/proxy.19 URL đều hợp lệ. Không thay schema, không sửa domain/framework boundaries.

Backup trước thao tác: artifacts/hoodoomart-before-shopping-bulk.dump. Payload ổn định: artifacts/shopping-updated-import.json. Báo cáo kết quả: artifacts/shopping-updated-import-result.json. Các file này ở artifacts, không đưa lên Git.

## Lệnh thực tế và kiểm chứng

- artifacts/backend-check-env/Scripts/python.exe -m pytest apps/api/unit_tests/test_shop_sample.py apps/api/tests/test_shop_sample.py -q --tb=short -p no:cacheprovider:19 passed/7.98s, database riêng hoodoomart_test.
- Ruff check + format cho3 file importer/tests: đạt. Strict mypy toàn backend: đạt42 source files.
- docker compose --env-file .env -f infra/docker-compose.yml build api: đạt.
- docker compose --env-file .env -f infra/docker-compose.yml up -d --no-deps --wait api: healthy.
- Get-Content artifacts/shopping-updated-import.json -Raw -Encoding utf8 | docker compose --env-file .env -f infra/docker-compose.yml exec -T api python -m app.infrastructure.shop_sample --rights-reviewed --dry-run: created18/reused1, rollback.
- Lệnh tương tự bỏ --dry-run: created18/reused1, commit thành công.
- SQL xác nhận rhodi_products19, rhodi-p11847 on_hand8/reserved1.
- Frontend build/TypeScript: đạt; trang nguồn sửa số ít thành số nhiều.
- Chrome headless: API total19, home19cards,19 ảnh naturalWidth>0, danh sách phân trang12+7, mobile390px không tràn ngang. Bằng chứng artifacts/shopping-bulk-browser.json, shopping-bulk-desktop.png, shopping-bulk-mobile.png.

Giới hạn: chỉ nhập dữ liệu/hiển thị; chưa nâng cấp đa biến thể hay tạo vector ảnh AI cho dữ liệu mới.
