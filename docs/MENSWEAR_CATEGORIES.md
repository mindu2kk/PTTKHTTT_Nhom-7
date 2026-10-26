# Danh mục thời trang nam — 2026-10-26

Theo 3 ảnh người dùng cung cấp; chỉ hiển thị cây thời trang nam theo lựa chọn của người dùng.

## Cấu trúc

Một gốc `nam` (Thời trang nam), 3 nhóm, 19 danh mục lá. Tổng 23 bản ghi đang bật.

| Nhóm | Danh mục | category_id |
|---|---|---|
| Áo | Áo pull | `nam-ao-pull` |
| Áo | Polo | `nam-polo` |
| Áo | Áo sơ mi | `nam-ao-so-mi` |
| Áo | Tanktop | `nam-tanktop` |
| Áo | Cardigan & khoác nhẹ | `nam-cardigan-khoac-nhe` |
| Áo | Áo nỉ & len | `nam-ao-ni-len` |
| Áo | Áo khoác | `nam-ao-khoac` |
| Quần | Quần lửng | `nam-quan-lung` |
| Quần | Quần âu vải | `nam-quan-au-vai` |
| Quần | Quần khaki | `nam-quan-khaki` |
| Quần | Quần jeans | `nam-quan-jeans` |
| Quần | Quần nỉ | `nam-quan-ni` |
| Phụ kiện | Vòng tay - vòng cổ - charm | `nam-vong-charm` |
| Phụ kiện | Mũ | `nam-mu` |
| Phụ kiện | Balo - túi | `nam-balo-tui` |
| Phụ kiện | Dây lưng - xích | `nam-day-lung-xich` |
| Phụ kiện | Khăn - găng tay | `nam-khan-gang-tay` |
| Phụ kiện | Giày - tất | `nam-giay-tat` |
| Phụ kiện | Kính mắt | `nam-kinh-mat` |

## Lưu trữ và phạm vi

- Alembic `0007_menswear_categories` thêm `categories.is_active`, mặc định false; tạo cây mới với true. Không sửa/xóa sản phẩm, ảnh, kho, nguồn, đơn hay lịch sử cũ.
- 49 danh mục cũ vẫn giữ trong DB với is_active=false. Không tự gán sản phẩm cũ sang mục mới; 55 sản phẩm hiện có vẫn được giữ, catalog mới đang trống.
- API categories trả cả danh mục mới chưa có sản phẩm, ở mọi DATA_PROFILE; catalog/search/facets/chi tiết chỉ lấy sản phẩm thuộc danh mục đang bật, giữ nguyên các gate quyền nguồn, ảnh, publication và verification.
- Tạo/preview/import/publish quản lý từ chối danh mục đã tắt. Thư mục ảnh và vector không đổi; index ảnh tiếp tục lọc candidate từ catalog công khai.
- Menu và bộ lọc dùng API categories; trang chủ dùng 3 nhóm Áo/Quần/Phụ kiện. Nhãn và thứ tự theo ảnh.
- Parser có tên tương đương tiếng Việt cho 19 mục. Mô tả hình dáng bổ sung mapping hữu hạn OpenCLIP cho thời trang; chưa đo chất lượng ảnh/giọng trên dữ liệu thời trang mới.
- Chưa tải/nhập dữ liệu thời trang bên ngoài. Pipeline ABO lịch sử vẫn dùng mapping cũ; các danh mục mới do pipeline đó tạo mặc định tắt. Không dùng pipeline cũ để tự xuất bản catalog mới.
- Khi nhập sản phẩm mới, dùng category_id lá trong bảng trên và giữ quy trình review nguồn/ảnh. Các fixture demo cũ không tự bật lại cây cũ khi seed lại.

## Áp dụng / rollback

Đã backup DB chính vào `artifacts/hoodoomart-before-menswear-20261026.dump` (74.838 bytes, chứa dữ liệu cục bộ; không đưa lên Git).

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait api web
docker compose --env-file .env -f infra/docker-compose.yml exec -T api alembic check
```

Migration đã áp dụng trên DB chính. Downgrade về 0006 chỉ cho phép khi không có sản phẩm hay danh mục con mới phụ thuộc cây mới; không tự xóa dữ liệu đó. Sau rollback phải dùng mã ứng dụng tương ứng 0006 (chưa có cột is_active).

Xem các danh mục đang hiển thị:

```sql
SELECT id, parent_id, name_vi, level, sort_order
FROM categories WHERE is_active
ORDER BY level, parent_id, sort_order;
```

## Kiểm chứng

Môi trường kiểm tra: `artifacts/backend-check-env/Scripts/python.exe` (Python với dependencies kiểm thử có sẵn).

- `-m pytest apps/api/unit_tests -q -p no:cacheprovider`: 248 passed/0.65s.
- `-m pytest apps/api/tests -q -p no:cacheprovider`: 193 passed/22.96s; TEST_DATABASE_URL riêng hoodoomart_test. Lượt đầu 192 passed/1 failed do kỳ vọng categories cũ của test M8; đã cập nhật test theo hành vi mới và chạy lại đạt.
- Test lịch sử bật riêng cây fixture trong conftest; test menswear chuyển cây trong transaction rollback, kiểm [1,3,19], giữ tổng sản phẩm, ẩn legacy, lọc theo cây và chặn tạo ở mục tắt. Không dùng cấu hình fixture này cho DB chính.
- `-m ruff check apps/api scripts`: đạt.
- `-m mypy --config-file apps/api/pyproject.toml apps/api/app`: đạt 41 source files.
- Docker build API/web và TypeScript: đạt; API/web healthy, readiness ready.
- `alembic check`: No new upgrade operations detected.
- SQL DB chính: head=0007_menswear_categories, active [1,3,19], inactive [4,11,34], products=55.
- GET /api/v1/categories: 23 bản ghi, đúng nhãn danh mục.
- Lượt unit/mypy trong sandbox bị treo, đã dừng và chạy lại ngoài sandbox bằng cùng môi trường; không dùng lượt treo làm bằng chứng đạt.

- Chrome headless thực tế ở 1440/768/390 px: menu đúng 19 mục lá, select có 23 danh mục + mục tất cả, homepage có 3 nhóm, không tràn ngang. Ảnh kiểm tra tại `artifacts/menswear-desktop.png`, `artifacts/menswear-390.png`, `artifacts/menswear-768.png`; đã xem ảnh desktop sau khi kết thúc animation.
