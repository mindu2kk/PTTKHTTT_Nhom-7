# Chọn size sản phẩm — 2026-10-26

Đã đọc bản mới của `VP-BaiTapNhom.vpp`: product có nhiều product_size;
cart_item và order_item tham chiếu product_size. Giữ cấu trúc PostgreSQL,
offer, provenance, tài khoản và giao dịch đang có; không chuyển toàn bộ DB sang MySQL.

## Thiết kế thực tế

- `product_sizes`: id INT tự tăng, product_id, size VARCHAR(3), stock_quantity,
  reserved. Chỉ nhận S/M/L/XL/XXL/F; UNIQUE(product_id,size); kho không âm và
  không thấp hơn số đang giữ.
- `cart_items`: khóa chính (user_id,product_size_id). Giữ product_id và dùng
  khóa ngoại ghép (product_size_id,product_id) để không chọn nhầm size của sản phẩm khác.
- `order_items`: thêm product_size_id và size_snapshot. Đơn cũ giữ NULL vì
  không có bằng chứng khách đã chọn size; đơn mới ghi size từ database.
- `stock_reservations`: giữ kho theo order/offer/size. Checkout kiểm giá/quyền
  công khai và khóa kho theo thứ tự; hủy nhả kho; giao đi trừ kho đúng size.
- `inventory` giữ tổng để tương thích catalog và offer hiện có. Cả kho tổng
  và kho size được cập nhật trong cùng transaction; không cộng thêm sức chứa.

## Chuyển dữ liệu

Migration `0008_product_sizes` nối sau `0007_menswear_categories`.
Tách các size đã khai báo, chuẩn hóa 2XL thành XXL; trường không có size chuẩn
dùng F như quy ước người dùng. Trường size nguồn/JSON cũ vẫn được giữ.
F là quy ước bán hàng trong demo, không khẳng định kích thước vật lý của nguồn.

Kho cũ là hạn mức mô phỏng theo sản phẩm. Phần chưa giữ được chia đều giữa
các size, phần dư cấp lần lượt S/M/L/XL/XXL/F. Kho đang giữ trước migration
được phân vào dòng size đầu tiên để giữ/nhả giao dịch cũ, không gán size cho đơn cũ.
Giỏ server cũ mặc định size đầu tiên; giỏ trình duyệt thiếu size cần chọn lại trên trang giỏ.
Đây không phải tồn kho thực tế theo size của nhà cung cấp.

Đối chiếu DB chính trước/sau: 74 sản phẩm, 2 đơn, 3 dòng đơn, 1 dòng giỏ;
mọi inventory.on_hand/reserved giữ nguyên, tổng các size khớp inventory.
Đã tạo 89 dòng size. Backup: `artifacts/before-product-sizes.dump`;
snapshot số lượng/kho: `artifacts/product-sizes-before.json` (không đưa lên Git).

## API và giao diện

- Product detail trả `sizes`: id, size, available_quantity; facet/lọc size dùng bảng mới.
- Cart/checkout nhận product_id, product_size_id, quantity. Thiếu size chỉ được
  chấp nhận cho sản phẩm có đúng một lựa chọn để tương thích client cũ.
- Khách chọn size tại chi tiết; size hết hàng bị khóa. F tự chọn khi là lựa chọn duy nhất.
  Giỏ hiển thị/chỉnh size, tăng giảm và xóa độc lập từng dòng. Đơn hiển thị size snapshot.
- Seed và các importer hiện có khởi tạo kho size một lần; replay không reset kho.
- Quản lý cập nhật kho tổng cũ chỉ áp dụng sản phẩm một size. Sản phẩm nhiều
  size từ chối sửa kho tổng để tránh làm sai phân bổ; UI quản lý kho theo size chưa bổ sung.
  Kênh quản lý real_demo vẫn chỉ đọc như trước.

## Kiểm chứng đã chạy

Python kiểm thử dùng `artifacts/backend-check-env/Scripts/python.exe`, vì .venv hiện tại
thiếu app/dev dependencies. Tests dùng TEST_DATABASE_URL riêng tới hoodoomart_test.

```powershell
$env:PYTHONPATH='apps/api'
artifacts/backend-check-env/Scripts/python.exe -m pytest apps/api/unit_tests apps/api/tests -q --tb=short -p no:cacheprovider --junitxml=artifacts/product-sizes-tests.xml
artifacts/backend-check-env/Scripts/python.exe -m ruff check apps/api scripts
artifacts/backend-check-env/Scripts/python.exe -m mypy --config-file apps/api/pyproject.toml apps/api/app
artifacts/backend-check-env/Scripts/python.exe -m alembic -c apps/api/alembic.ini check
```

Kết quả cuối: 463 tests đạt/26.77s; Ruff đạt; strict mypy 44 files đạt;
Alembic: No new upgrade operations detected. Có negative media/ownership,
size sản phẩm khác, thiếu size khi nhiều lựa chọn, trùng dòng, cạnh tranh đơn vị
cuối, retry idempotency, hủy và giao đi theo đúng size.

Node 24: sinh OpenAPI types; ESLint src đạt; 20 frontend tests đạt;
Next production build và Docker build api/web/migrate đạt.
Các lệnh frontend chạy tại apps/web, qua Node 24 runtime có sẵn:
`node node_modules/openapi-typescript/bin/cli.js ../../docs/openapi.json -o src/lib/schema.ts`,
`node node_modules/typescript/bin/tsc --noEmit`,
`node node_modules/eslint/bin/eslint.js src`, `node --test tests/*.test.mjs`,
`node node_modules/next/dist/bin/next build`.
Docker thực tế: `docker compose --env-file .env -f infra/docker-compose.yml build api web`,
`stop web api`, `run --rm --no-deps api alembic upgrade head`,
`up -d --no-deps --wait api web`, rồi `build migrate` và `up -d --wait`
(các lệnh rút gọn dùng cùng tiền tố docker compose/env-file/compose file).
Chrome: hai size của một sản phẩm thành hai dòng; xóa một dòng giữ dòng kia;
mobile 390px không tràn; F tự chọn; POST không JavaScript giữ đúng size;
không có pageerror. Evidence: `artifacts/product-sizes-browser.json`,
`sizes-product-desktop.png`, `sizes-cart-mobile.png`, `sizes-free-mobile.png`.
Harness đã chạy: `artifacts/backend-check-env/Scripts/python.exe -u artifacts/verify_product_sizes.py`;
đối chiếu DB bằng `artifacts/check_sizes_inventory.py before` và `after` qua cùng Python.

Lượt đầu: GET cart dùng nhầm biến và readiness còn revision cũ, đã sửa;
test collection import và lệnh ESLint sai thư mục được sửa và chạy lại.
Chrome phát hiện nút bị disable trong fallback không JavaScript, đã sửa và kiểm lại.
Lệnh .venv ban đầu thiếu Ruff/app; chuyển sang backend-check-env có sẵn.
Lượt pytest/mypy trong sandbox không hoàn tất; đã dừng và chạy lại ngoài sandbox.

## Chạy và khôi phục

Đã áp dụng migration chính bằng image API mới, cập nhật image migrate,
chạy lại `docker compose --env-file .env -f infra/docker-compose.yml up -d --wait`;
postgres/api/web/inference đều healthy. Không seed/reset database chính.

Rollback migration từ chối khi đã có đơn mới ghi size hoặc nhiều size cùng
sản phẩm trong giỏ/reservation, tránh bỏ mất lựa chọn. Khi đó dừng ghi mới và
khôi phục backup vào database riêng để kiểm tra trước, rồi chuyển cấu hình
nếu cần; không dùng down -v hay tự xóa volume. Backup trước migration không
chứa những đơn được tạo sau đó. Model AI/weights và các gate TC2 không đổi.
