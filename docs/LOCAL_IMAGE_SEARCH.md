# Tìm ảnh cục bộ — 2026-10-26

## Nguyên nhân và thay đổi

Worker ban đầu báo `clip_files=false`: lỗi 503 trong ảnh chụp là model chưa có,
không phải lỗi chọn file. Indexer cũ chỉ chọn nguồn amazon-berkeley-objects và
đọc file local, nên bỏ qua catalog Hoodoo dùng URL Postimages.

Người dùng đã đồng ý tải OpenCLIP cục bộ một lần. Đã tải đúng hai file từ
laion/CLIP-ViT-B-32-laion2B-s34B-b79K revision
`1a25a446712ba5ee05982a381eed697ef9b435cf`, kiểm SHA256 theo manifest pinned
hiện có, giữ MIT metadata tại `models/clip/acquisition.json`. Model safetensors
605143316 bytes, SHA256
`ac4f8c4b88af6d963118cbf40ad93176d092abbedfcb752601ae1866352656e6`.
Không tải lại model giọng nói, không thêm dependency hoặc dùng API suy luận bên ngoài.

`download_models.py` yêu cầu chọn model và `--consent`, kiểm checksum trước đổi
tên partial; file cũ sai hash không bị ghi đè. Không sửa evidence lịch sử.

`index_real_images.py` dùng cổng public catalog đang có theo DATA_PROFILE, lấy
cả gallery được duyệt, fetch Postimages qua cùng helper bounded/no-redirect
của admin. Chặn đường dẫn vượt thư mục và host khác; kiểm hash trước encode.
Chỉ tạo/cập nhật vector 512D, không sửa sản phẩm, giá, kho, đơn hoặc provenance.
Index được tạo trước, không encode toàn bộ catalog trên mỗi truy vấn.

## Đã chạy và kết quả

```powershell
artifacts/backend-check-env/Scripts/python.exe scripts/download_models.py --only clip --consent
$env:PYTHONPATH = 'apps/api'
artifacts/backend-check-env/Scripts/python.exe scripts/index_real_images.py
artifacts/backend-check-env/Scripts/python.exe scripts/index_real_images.py
artifacts/backend-check-env/Scripts/python.exe -m pytest apps/api/tests/test_catalog_image_index.py apps/api/tests/test_media.py apps/api/tests/test_commerce.py apps/api/unit_tests/test_product_image_url.py apps/api/unit_tests/test_clip_download.py -q --tb=short -p no:cacheprovider --junitxml=artifacts/image-feature-tests.xml
artifacts/backend-check-env/Scripts/python.exe -m ruff check apps/api scripts
artifacts/backend-check-env/Scripts/python.exe artifacts/verify_local_image_search.py
```

- Encode **20 ảnh của catalog 19 sản phẩm real_demo**; lượt lặp encode0/skip20,
  không tạo trùng. Worker `clip_files=true`, `clip_loaded=true`, CPU; LOCAL_ONLY giữ true.
- **41 tests đạt**, database riêng hoodoomart_test. Bao gồm ảnh hỏng/quá lớn,
  URL sai host/redirect, đường dẫn traversal, URL gallery được lấy vào index,
  ảnh chưa duyệt và sản phẩm draft bị loại, kiểm ownership commerce.
- Ruff đạt; không đổi frontend trong lần sửa tìm ảnh này.
- Docker build API và `up -d --no-deps --wait api` đạt, API healthy; giữ database
  và profile hiện tại. Chạy lại kiểm tra Chrome sau triển khai.
- Chrome thật: upload cùng ảnh gile catalog, gọi BFF/API/worker thật, sản phẩm
  `rhodi-p11387` đứng đầu; ảnh bytes hỏng trả422. Đã xem screenshot.
  Evidence: `artifacts/image-search-real.json/png`, `image-search-response.json`,
  `local-image-index.json`, `local-image-index-replay.json`, `image-feature-tests.xml`.
- Lint lượt đầu báo bốn dòng test quá dài; đã format rồi chạy lại đạt.

## Giới hạn vận hành

Sau khi admin thêm/đổi ảnh hoặc xuất bản sản phẩm mới, chạy lại indexer với lệnh
trên. Hiện chưa có worker tự lập chỉ mục theo lịch; ảnh mới chưa index sẽ chưa
tham gia xếp hạng. URL thay nội dung cần duyệt lại hash trước khi index.

Kiểm tra cùng ảnh chỉ xác nhận luồng hoạt động; không chứng minh độ chính xác
trên ảnh chụp điện thoại, góc khác, ảnh ngoài catalog hoặc khả năng nhận diện
đúng SKU. Không chạy lại benchmark hoặc toàn bộ integration suite.
