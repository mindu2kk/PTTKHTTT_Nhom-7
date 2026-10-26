# Dọn code voice và image — 2026-10-26

Phạm vi là các phần media vừa thêm/sửa, không audit toàn repository.

- Indexer dùng chung `sanitize` và `HttpImageEncoder` với luồng tìm ảnh, bỏ
  phần gọi HTTP/kiểm vector lặp lại. Tách đọc ảnh, chuẩn bị ảnh, lấy gallery
  và tạo index thành các hàm có tên rõ và type hints. Giữ kiểm hash nguồn,
  quyền công khai, giới hạn bytes, URL và đường dẫn.
- Indexer đóng database engine bằng `finally`, cả khi encoding thất bại.
- Downloader chọn trực tiếp model cần tải, tách tải file và kiểm checksum;
  giữ consent, pinned revision/hash, partial và không ghi đè file sai hash.
- Đặt tên các ngưỡng cửa sổ/năng lượng/khuếch đại trong decoder và ngưỡng dB,
  cảnh báo im lặng, chu kỳ cập nhật trong bộ đo micro. Không thay giá trị ngưỡng.
- Giữ line endings gốc của RUNBOOK để diff chỉ còn các sửa đổi nội dung.

Kiểm tra đã chạy:

```powershell
$env:PYTHONPATH = 'apps/api'
artifacts/backend-check-env/Scripts/python.exe -m pytest apps/api/tests/test_catalog_image_index.py apps/api/tests/test_media.py apps/api/tests/test_commerce.py apps/api/unit_tests/test_product_image_url.py apps/api/unit_tests/test_clip_download.py apps/api/unit_tests/test_image_index_helpers.py apps/api/unit_tests/test_phowhisper_download.py -q --tb=short -p no:cacheprovider --junitxml=artifacts/cleanup-tests.xml
artifacts/backend-check-env/Scripts/python.exe -m ruff check apps/api scripts
artifacts/backend-check-env/Scripts/python.exe scripts/index_real_images.py
docker compose --env-file .env -f infra/docker-compose.yml build inference web
docker compose --env-file .env -f infra/docker-compose.yml up -d --no-deps --wait inference web
```

48 tests backend/script đạt; 22 worker unittests với decoder mới mount trong
Docker `--network none` đạt. ESLint ba component voice và production build
TypeScript đạt. Index replay encode0/skip20. Chuẩn bị ảnh/adapter OpenCLIP thật
được chạy trực tiếp để kiểm nhánh encode mới dù replay không cần encode lại.
`git -c core.whitespace=cr-at-eol diff --check` đạt, giữ quy ước CRLF tài liệu cũ.

Chrome harness kiểm mức âm/im lặng/chọn micro/hủy/nhả tracks và tìm chữ;
model local thực nhận WAV giảm âm. Harness ảnh kiểm upload→model thật→gile
đứng đầu và bytes hỏng422. Evidence: `artifacts/cleanup-tests.xml`,
`artifacts/microphone-fix.json`, `artifacts/image-search-real.json`,
`artifacts/local-image-index-replay.json`.

Lượt test đầu có một lỗi ở mock: AsyncEngine.dispose chỉ đọc. Đã thay mock
engine tại namespace của script, chạy lại toàn bộ 48 tests đạt. Lint lượt đầu
nhắc các dòng test dài; format và chạy lại đạt. Không có lỗi production từ
hai trường hợp này.

Không tải model mới, không đổi schema hoặc reset dữ liệu. Chưa thử micro vật
lý, chưa đo chất lượng model hoặc chạy lại toàn bộ backend suite. Sau thêm/
đổi ảnh vẫn cần chạy indexer theo RUNBOOK; lần này không thêm tính năng mới.
