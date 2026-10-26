# Kiểm tra mẫu Rhodi và ảnh URL trực tiếp — 2026-10-26

Đã nhập đúng dòng dữ liệu đầu tiên của DataShopping.xlsx, sau khi người dùng xác nhận quyền sử dụng sản phẩm và ảnh cho web demo trong chat. Không áp dụng nguồn/giấy phép Amazon cho bản ghi này.

## Bản ghi

- Product ID/slug: `rhodi-p11847`; tên nguồn: Somi trơn thô 8080 QS.
- Category: `nam-ao-so-mi`; size L; màu trắng.
- Giá đặt thử 260000 VND; hạn mức đặt thử 8. Đây là bản sao số trong sheet cho demo, không xác minh giá/kho live của shop.
- Source: `rhodi-user-reviewed`, rights_status approved, ghi rõ xác nhận của người dùng; không tuyên bố giấy phép mở. Link trang nguồn giữ trong source record/provenance.
- Profile `real_demo`; nguồn thật đã duyệt + giá/kho đặt thử. `.env` chuyển DATA_PROFILE từ demo_seed sang real_demo, không sửa dữ liệu cũ.
- `product_images.storage_key` lưu nguyên `https://i.postimg.cc/tRDK6Fgm/Somi-tron-tho-8080-QS-16.jpg`.
- Ảnh được kiểm tra MIME/nội dung/kích thước/hash trong RAM, không ghi ảnh vào data/catalog/images. SHA256 `8a68b87a360bc707e4388937ba9c1168526c7bf2fc1b0ce3f2bd272e34fbd8d5`, 640x800.
- SKU `TRIAL-RHODI-P11847` được tạo cho demo; không coi mã URL p11847 là SKU do shop xác nhận.
- Không suy diễn chất liệu/thương hiệu thành thuộc tính đã xác minh. Chưa tạo vector/index ảnh AI cho mẫu này.

## Thay đổi

`app.infrastructure.shop_sample` là CLI operator nhận một record JSON từ stdin, chỉ nhập khi có --rights-reviewed. Kiểm tra source URL rhodi.vn và image host i.postimg.cc, không redirect/proxy, ảnh tối đa5MB/12MP. Import trong một transaction, khóa/replay theo source+external ID, từ chối raw drift, không ghi đè kho khi chạy lại. Không thêm API upload/media mới, không đổi schema, không thay pipeline ABO cũ.

Frontend đã dùng Next Image unoptimized nên tải trực tiếp ảnh trong browser. CSP img-src bổ sung đúng `https://i.postimg.cc`, không mở toàn bộ HTTPS host. Gallery/fallback giữ nguyên. Nhãn nguồn trên API hiển thị Rhodi theo source_id; footer/gallery không còn mặc định mọi ảnh là ABO/WebP. Trang sources phân biệt mẫu Rhodi hiện tại và nguồn ABO lịch sử.

Backup trước nhập: `artifacts/hoodoomart-before-shop-sample.dump`. Payload một dòng: `artifacts/shopping-first-record.json` (không đưa lên Git).

## Cổng PostgreSQL

Sau khi Docker Desktop khởi động lại, Windows loại trừ dải55357–55456 bao gồm55432. DB bên trong Docker vẫn có dữ liệu nhưng host port mất kết nối. Đã kiểm tra15432 trống, đổi POSTGRES_PORT và host DATABASE_URL/TEST_DATABASE_URL trong .env sang15432 rồi khởi động lại postgres bằng volume cũ. Không đổi password/database/user. pgAdmin/DBeaver dùng localhost:15432. Lệnh docker compose exec postgres psql vẫn như cũ.

## Lệnh và bằng chứng

- Runtime kiểm tra: `artifacts/backend-check-env/Scripts/python.exe`; PYTHONPATH=apps/api.
- `-m pytest apps/api/unit_tests -q -p no:cacheprovider`:264 passed/9.71s.
- `-m pytest apps/api/tests/test_shop_sample.py apps/api/tests/test_catalog.py apps/api/tests/test_real_catalog.py -q --tb=short -p no:cacheprovider`:62 passed/16.28s, DB riêng hoodoomart_test. Lượt đầu không chạy được setup do port55432 bị chặn, chạy lại sau đổi cổng đạt. Không gọi lỗi kết nối là lỗi logic product.
- `-m ruff check apps/api scripts`: đạt.
- `-m mypy --config-file apps/api/pyproject.toml apps/api/app`: đạt42 source files.
- `docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait api web`: build/TypeScript đạt, API/web healthy.
- Import: `Get-Content artifacts/shopping-first-record.json -Raw -Encoding utf8 | docker compose --env-file .env -f infra/docker-compose.yml exec -T api python -m app.infrastructure.shop_sample --rights-reviewed`: id rhodi-p11847, reused=false. SQL xác nhận row published/real_demo và nguyên URL ngoài.
- Chrome thật headless: catalog/detail/zoom/mobile390px đạt. Network ghi request trực tiếp i.postimg.cc trả200, naturalWidth640/naturalHeight800. Chặn ảnh bằng browser route cho thấy fallback hoạt động. Lượt harness đầu lỗi locator trùng giữa ảnh và tên, đã sửa locator và chạy lại đạt; không phải ảnh render lỗi.
- Bằng chứng `artifacts/shopping-sample-browser.json`, `shopping-sample-catalog.png`, `shopping-sample-detail.png`, `shopping-sample-mobile.png`; đã xem ảnh detail.

Chưa nhập18 sản phẩm còn lại, chưa mở hỗ trợ đa biến thể hay đo chất lượng AI. File Excel nguồn không thay đổi.
