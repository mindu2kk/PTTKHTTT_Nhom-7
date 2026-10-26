# Quản trị sản phẩm và nhiều URL ảnh — 2026-10-26

Admin đăng nhập sẽ mặc định vào `/manage` nếu không có đường dẫn tiếp tục khác.
Header có liên kết Quản lý sản phẩm trên desktop/mobile. Tài khoản được người dùng
chỉ định đã được cấp thêm role admin; mật khẩu hiện tại được giữ nguyên.
Đăng ký công khai vẫn chỉ tạo customer, không nhận role từ client.

## Sử dụng

1. Vào `/auth/login`, đăng nhập tài khoản admin.
2. Mở Thêm mặt hàng mới: tên, mô tả, danh mục, giá nguyên VND, màu/chất liệu/
   thương hiệu, URL ảnh và số lượng từng size S/M/L/XL/XXL/F.
3. Mỗi dòng một URL ảnh; ảnh đầu tiên làm ảnh bìa. Tối đa 10 ảnh, định dạng
   JPEG/PNG/WebP, mỗi ảnh tối đa 5 MB và 12 triệu pixel. Hiện hỗ trợ URL trực tiếp
   `https://i.postimg.cc/...`, cùng host với ảnh Postimages hiện có và CSP của web.
4. Xác nhận quyền sử dụng metadata/ảnh. Lưu nháp hoặc chọn xuất bản sau khi thêm.
5. Tìm sản phẩm theo tên/mã, mở Chỉnh sửa sản phẩm, sửa thông tin/kho/danh sách ảnh
   rồi Lưu thay đổi. Đổi thứ tự các dòng URL để đổi ảnh bìa/thứ tự gallery.
   Có thể ẩn và xuất bản lại sản phẩm. Khi thêm/đổi ảnh cần xác nhận quyền ảnh mới.

Không lưu file ảnh vào project: server chỉ kiểm tra bytes trong RAM, lưu URL,
hash/kích thước và hồ sơ xác nhận quyền. Không tự giả định ảnh có giấy phép CC0;
nguồn ảnh URL có license riêng do operator xác nhận quyền dùng cho demo.

## Backend và dữ liệu

- Mở create/update/publish/archive cho admin trong real_demo; seller vẫn chỉ đọc
  profile này. Giữ luồng seller tạo nháp/chỉnh offer trong demo_seed.
- PATCH sản phẩm nhận metadata, brand và sizes=[{size,stock}]. Tổng stock phải
  khớp các size; không giảm dưới reserved, không xóa size có đơn đang giữ.
  Size bị bỏ khỏi danh sách được giữ với kho 0 để bảo toàn lịch sử tham chiếu.
- POST/PATCH nhận image_urls; API image_id/image_url cũ vẫn tương thích.
  Kiểm host HTTPS trước network; không proxy/redirect; giới hạn MIME/bytes/pixels.
  URL trùng/danh sách rỗng/quá giới hạn bị từ chối. Ảnh phụ lỗi rollback toàn bộ.
- Khóa ngoại, ownership/CSRF+Origin và phạm vi data_profile vẫn được kiểm ở server.
  Catalog chỉ thấy published+verified, ảnh và tất cả nguồn có quyền phù hợp.
- Giữ raw source cũ và thêm dấu vết admin_edit vào provenance; ảnh mới có hồ sơ
  hash/URL/người xác nhận. Thu hồi quyền nguồn tiếp tục ẩn sản phẩm liên quan.
- Gallery giữ các ảnh còn dùng, đổi primary/thứ tự trong transaction, bỏ đúng ảnh
  được admin loại khỏi danh sách và vector của ảnh đó. Không sửa raw nguồn cũ.
- Migration `0009_product_image_order` thêm sort_order và giữ thứ tự cũ mặc định;
  head readiness là 0009. Không thay số lượng bảng, không create_all/reset volume.
- Giỏ khi đăng nhập hợp nhất theo product+size, không gộp M và L thành một dòng;
  giỏ khách cũ thiếu size vẫn được giữ để chọn lại.
- Chỉ thao tác lưu sản phẩm/import được deadline 60 giây để kiểm tra ảnh URL;
  giới hạn body/CSRF/timeout của các endpoint khác vẫn giữ nguyên.

Backup trước thay đổi: `artifacts/before-admin-products.dump` và
`artifacts/before-admin-gallery.dump` (không đưa lên Git).
Snapshot trước/sau migration xác nhận giữ 74 sản phẩm, 74 ảnh cũ, 2 đơn,
3 dòng đơn và 2 dòng giỏ tại thời điểm kiểm tra; hash/URL/primary/kích thước ảnh cũ
giữ nguyên. Không seed database chính. Role admin được cấp đúng email người dùng
chỉ định, không tạo mật khẩu mặc định.

## Kiểm chứng thực tế

Python kiểm thử: `artifacts/backend-check-env/Scripts/python.exe`,
TEST_DATABASE_URL riêng tới hoodoomart_test. Các lệnh đã chạy:

```powershell
$env:PYTHONPATH='apps/api'
artifacts/backend-check-env/Scripts/python.exe -m pytest apps/api/unit_tests apps/api/tests -q --tb=short -p no:cacheprovider --junitxml=artifacts/admin-products-tests.xml
artifacts/backend-check-env/Scripts/python.exe -m ruff check apps/api scripts
artifacts/backend-check-env/Scripts/python.exe -m mypy --config-file apps/api/pyproject.toml apps/api/app
artifacts/backend-check-env/Scripts/python.exe -m alembic -c apps/api/alembic.ini check
docker compose --env-file .env -f infra/docker-compose.yml build api migrate web
docker compose --env-file .env -f infra/docker-compose.yml stop web api
docker compose --env-file .env -f infra/docker-compose.yml run --rm --no-deps api alembic upgrade head
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
artifacts/backend-check-env/Scripts/python.exe -u artifacts/verify_admin_products.py
```

Kết quả cuối: **480 tests đạt/38.11s** (279 unit +201 integration), Ruff đạt,
strict mypy 45 files đạt; Alembic không phát hiện lệch schema. Bộ test có negative
quyền, stock đang giữ, cách ly profile, thu hồi quyền nguồn, URL/private host/
redirect/MIME giả/ảnh hỏng/quá 5 MB, gallery đổi thứ tự/bỏ ảnh và rollback.

Node 24: OpenAPI export/types, TypeScript, ESLint, production/Docker build đạt;
20 frontend unit tests đạt. Lệnh tại apps/web: `node node_modules/typescript/bin/tsc --noEmit`,
`node node_modules/eslint/bin/eslint.js src`, `node --test tests/*.test.mjs`.

Chrome thật trên Docker: customer bị từ chối quản lý; admin đăng nhập vào manage;
giữ hai size trong giỏ khi login; tạo/xuất bản với hai URL thật, sửa thông tin/giá/
kho và gallery thành ba URL; xác nhận thứ tự/ảnh bìa/thumbnails; mobile 390px
không tràn, không pageerror. Bằng chứng `artifacts/admin-products-browser.json`,
`admin-products-desktop.png`, `admin-products-mobile.png`.
Tài khoản và sản phẩm QA tạm đã được xóa theo đúng ID/email tạo trong harness;
đối chiếu cho thấy catalog/đơn/kho cũ không bị thay đổi.

Lượt đầu gặp fixture category chưa active/thiếu import và pytest ID quá dài từ
buffer 5 MB; đã sửa harness và chạy lại. Chrome đầu dùng locator select chưa đúng,
đã sửa. Kiểm tra URL thật ban đầu vượt deadline chung 5s; đã giới hạn riêng
deadline ghi sản phẩm và chạy lại thành công.

## Giới hạn và khôi phục

Danh sách quản lý hiện giới hạn 100 bản ghi gần cập nhật, tìm trong danh sách đó.
Host ảnh khác Postimages và upload file chưa nằm trong luồng này. Không tự tạo
vector AI cho ảnh mới; giữ giới hạn pipeline ảnh hiện tại, không tải model/API trả phí.
Ảnh có thể bị host bên ngoài thay đổi/xóa sau khi đã kiểm tra.

Rollback ứng dụng cần đi cùng revision schema tương ứng. Downgrade 0009 chỉ bỏ
thứ tự ảnh; giữ nguyên ảnh/sản phẩm/đơn. Backup trước thay đổi không chứa sản phẩm
mới thêm sau đó; kiểm tra restore trên DB riêng trước khi chuyển cấu hình.
