# Bổ sung 100 sản phẩm thời trang nam

## Dữ liệu và quyền sử dụng

- Nguồn cùng catalog của Hùng: các trang sản phẩm Rhodi, thu thập ngày 26/10/2026.
- Người dùng đã xác nhận trong chat quyền sử dụng thêm dữ liệu và ảnh của 100 sản phẩm cho website. Không tuyên bố giấy phép mở hoặc sự bảo trợ của cửa hàng.
- Đã chuẩn bị 100 mã nguồn mới, không trùng 19 mã ban đầu; phủ cả 19 danh mục lá hiện tại. Kiểm tra 100 ảnh JPEG/PNG/WebP, MIME, kích thước, dung lượng và SHA-256; không có ảnh trùng hash trong lô.
- Loại các sản phẩm cross-list không thuộc nhóm áo pull (tanktop, polo và quần). Bảng ảnh được rà soát trực quan trong thư mục private; không đưa bản HTML trang nguồn vào Git.

Các file dùng để chuyển dữ liệu sang máy khác:

- `data/demo/catalog.json`: 19 dòng gốc giữ nguyên nội dung, nối thêm 100 dòng mới.
- `data/demo/catalog-menswear-100.json`: riêng lô 100 dòng.
- `data/sources/rhodi-menswear-100-review.json`: xác nhận quyền, hash lô, URL nguồn và thông số/hash từng ảnh.

Giữ cùng các trường của Hùng: `name`, `description`, `category_id`, `size`, `color`, `price_vnd`, `trial_stock`, `image_url`, `source_url`. Các dòng mới bổ sung provenance để phân biệt dữ liệu lấy từ trang sản phẩm với bảng Excel ban đầu.

Giá là số nguyên VND ghi nhận trên trang nguồn, không bảo đảm là giá hiện tại. Hạn mức local của mỗi sản phẩm mới là 10, phân bổ bằng cơ chế size hiện có; không khẳng định đây là tồn kho của Rhodi. Mô tả được viết từ tên, danh mục và danh sách lựa chọn công khai. Không suy diễn chất liệu, công dụng, đánh giá hoặc doanh số. Thông tin thiếu giữ `Chưa có thông tin`.

Danh sách màu đầy đủ được giữ trong raw JSON và `option_values.available_colors`. Chuỗi nhiều màu vượt cột 40 ký tự dùng nhãn hiển thị `Nhiều màu`; không cắt bỏ các lựa chọn nguồn. Cơ chế size của nhánh Hùng hỗ trợ S/M/L/XL/XXL/F: size số hoặc 3XL được giữ trong thông tin nguồn, chưa mở rộng thành SKU/size mua riêng trong lần bổ sung này.

## Phạm vi thay đổi

Importer tiếp tục yêu cầu `--rights-reviewed`, kiểm danh mục lá đang hoạt động, cùng raw hash thì tái sử dụng và từ chối raw drift. Mỗi lô nằm trong một transaction. Ảnh được kiểm trước khi mở transaction.

Cho phép thêm đúng kho sản phẩm `https://pos.nvncdn.com/afec53-228676/ps/`, hậu tố ảnh và query phiên bản `v` dạng số; giữ HTTPS, cấm redirect, proxy, URL khác, đường dẫn traversal, MIME giả và ảnh quá giới hạn. CSP frontend bổ sung đúng prefix ảnh này. Không đổi schema, endpoint, giao diện mua hàng hay mật khẩu/tài khoản.

Backup trước nhập: `artifacts/backups/hoodoomart-before-menswear-100-20261026.dump`. Hash các hàng cũ được lưu riêng để đối chiếu sau nhập; không xuất mật khẩu hoặc nội dung đơn hàng vào báo cáo.

## Lệnh

```powershell
docker compose --env-file .env -f infra/docker-compose.yml cp data/demo/catalog-menswear-100.json api:/tmp/menswear-100.json
docker compose --env-file .env -f infra/docker-compose.yml exec -T api sh -c 'python -m app.infrastructure.shop_sample --rights-reviewed --dry-run < /tmp/menswear-100.json'
docker compose --env-file .env -f infra/docker-compose.yml exec -T api sh -c 'python -m app.infrastructure.shop_sample --rights-reviewed < /tmp/menswear-100.json'
```

Máy mới có thể nhập toàn bộ `data/demo/catalog.json` theo README. Máy đã có 19 sản phẩm không cần nhập lại các dòng đó. Thay đổi trên web không tự ghi ngược vào JSON.

## Trạng thái kiểm chứng

- 514 unit/integration tests qua trước lần điều chỉnh nhãn nhiều màu; database kiểm thử riêng `hoodoomart_test`.
- Ruff qua các file backend thay đổi; strict mypy qua 45 file trước điều chỉnh nhãn; frontend production build/TypeScript đã qua.
- Lượt dry-run đầu phát hiện chuỗi màu vượt cột 40 ký tự và rollback toàn bộ. Hash đối chiếu xác nhận các hàng cũ giữ nguyên, số sản phẩm vẫn 1177, đơn hàng vẫn 9.
- Đã nhập thành công ngày 27/10/2026: dry-run created100/reused0 và rollback; lượt thật created100/reused0 và commit. API công khai 119 sản phẩm, 100 mã mới đều khớp danh mục, giá, ảnh, quyền và hạn mức local10.
- Đối chiếu hash mọi hàng cũ trong 15 bảng: sản phẩm, giá/kho, size, ảnh, nguồn, tài khoản/quyền, giỏ và 9 đơn/10 dòng đơn đều giữ nguyên. Tổng bảng products1177→1277; catalog public19→119.
- 42 kiểm thử URL/quyền/import/rollback sau sửa nhãn màu đã qua. Strict mypy45 file qua. Các lượt kiểm thử lặp trong lúc thiếu RAM/Docker mất kết nối đã lỗi thiết lập database; không tính các lượt này là đạt.
- Docker API và frontend đã build, khởi động; trình duyệt xác nhận119 sản phẩm và ảnh mới tải được. 5 truy vấn polo/sơ mi/mũ/balo/thắt lưng có sản phẩm mới, giữ ngân sách.
- Khi máy chỉ còn414MB RAM, các lệnh Docker/SQL từng timeout và kết nối TLS máy chủ ảnh lỗi. Sau khi giải phóng tiến trình kiểm tra và phục hồi dịch vụ, nhập qua `artifacts/import-menswear-snapshot.mjs`, sử dụng đúng snapshot ảnh đã kiểm tra, đối chiếu hash của toàn lô với manifest đã duyệt. Chỉ phiên nhập operator dùng `SET LOCAL statement_timeout='60s'`; không đổi timeout API hoặc schema.
- Bằng chứng: `artifacts/menswear-100-import.json`, `menswear-100-dry-run.json`, `menswear-data-preservation.json`, `menswear-runtime.json`, `menswear-100-tests-final-focused.xml`.
- Đã dùng model OpenCLIP hiện có để index119 ảnh public (gồm19 ảnh catalog ban đầu và100 ảnh mới), kiểm hash ảnh nguồn trước encode. Tổng vector trong DB1456→1575; các vector cũ giữ nguyên. Không tải model hoặc gọi API trả phí. Báo cáo `artifacts/local-image-index.json`: encoded119, skipped0, approved_images119.
- API tìm ảnh Top-K3 với ảnh của sản phẩm mới `rhodi-p8743` trả đúng sản phẩm đó ở top1 và đủ3 kết quả đã duyệt. Đây là kiểm tra cùng ảnh nguồn, không phải benchmark ảnh chụp khác góc/độc lập; không có phép đo giọng nói mới.
- Bốn dịch vụ Docker healthy sau hoàn tất. Bằng chứng gọn được lưu ở [evidence/menswear-100](evidence/menswear-100/); ảnh chụp catalog ở `artifacts/menswear-catalog-119.png`.
