# Top-K cho tìm kiếm ảnh — 2026-10-26

Hai giao diện tìm ảnh (hộp tìm nhanh và `/search/image`) có ô “Số sản phẩm
tương đồng nhất", mặc định10, nhận số nguyên1–100. Chỉnh K rồi bấm Tìm.
Mỗi sản phẩm xuất hiện một lần dù gallery có nhiều ảnh. Nếu catalog có ít hơn
K kết quả hợp lệ thì chỉ trả số thực có; giữ phân trang12 kết quả/trang.

API `POST /api/v1/search/image` nhận thêm multipart `top_k` tùy chọn1–100.
Không gửi trường này giữ cách phân trang cũ để tương thích client hiện có.
SearchOptions truyền giới hạn vào orchestrator; cắt tập đã xếp hạng trước
phân trang và tính total. Trang tiếp theo không vượt K, metadata trả top_k.
Chỉ image API nhận trường mới, text/voice không thay contract.

Xếp hạng ảnh dùng độ tương đồng trước, giữ độ phân giải6 chữ số để điểm gần
nhau không bị gộp thành cùng nhóm. Tồn kho và preference chỉ phân xử sau điểm
ảnh; text vẫn ưu tiên còn hàng như trước. Giữ lọc quyền xuất bản, nguồn/ảnh
đã duyệt, danh mục/giá và chỉ lấy sản phẩm có vector đúng revision/hash.

Đã chạy:

```powershell
$env:PYTHONPATH = 'apps/api'
artifacts/backend-check-env/Scripts/python.exe -m pytest apps/api/tests apps/api/unit_tests -q --tb=short -p no:cacheprovider --junitxml=artifacts/top-k-tests.xml
artifacts/backend-check-env/Scripts/python.exe -m ruff check apps/api scripts
artifacts/backend-check-env/Scripts/python.exe -m mypy --config-file apps/api/pyproject.toml apps/api/app
artifacts/backend-check-env/Scripts/python.exe scripts/export_openapi.py
docker compose --env-file .env -f infra/docker-compose.yml build api web
docker compose --env-file .env -f infra/docker-compose.yml up -d --no-deps --wait api web
artifacts/backend-check-env/Scripts/python.exe artifacts/verify_image_top_k.py
```

Đã sinh lại TypeScript từ OpenAPI bằng openapi-typescript, chạy ESLint ba
component image/unified/top-k và Prettier. **504 backend tests đạt** trên
hoodoomart_test riêng, Ruff đạt, mypy45 files đạt, TypeScript/Docker build đạt.
Tests bổ sung: top-k trước phân trang; K lớn hơn số kết quả; trang ngoài K;
điểm ảnh sát nhau; ảnh gần nhất của sản phẩm hết hàng; không thêm sản phẩm
ngoài ứng viên/không index; K0/-1/101/2.5/abc bị chặn trước inference.
Lint lượt đầu báo một dòng tên test dài, đã format và kiểm lại đạt.

Chrome thật trên OpenCLIP local: K1→1, K3→3, K15→12+3 không trùng và không có
trang thứ3; K100→19 sản phẩm hiện có. Cả hai UI gửi top_k và trang riêng giữ
giá trị trên URL. Input rỗng/số lẻ/ngoài khoảng bị browser chặn. Đã xem layout
mobile390px, không tràn ngang. API/web đều healthy sau triển khai.

Evidence: `artifacts/top-k-tests.xml`, `artifacts/top-k-browser.json`,
`artifacts/top-k-mobile.png`, `artifacts/top-k-desktop.png`.
Kiểm ảnh cùng catalog là kiểm chức năng, không đo độ chính xác ảnh chụp khác góc.
Không tải model mới, không đổi schema/dữ liệu catalog, không cần lập lại index.
