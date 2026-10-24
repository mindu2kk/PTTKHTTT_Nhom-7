# M8 — nhập và chỉ mục tăng dần

Chạy tại root với venv từ setup. Giữ `LOCAL_ONLY=true`; models M7 đã có và đã được cho phép. Không tải trọng số mới trong M8.

```powershell
# Tải chọn lọc có quyền, staging/cache, không tự chạy trong setup:
.\.venv\Scripts\python.exe data_pipeline/abo.py acquire --reviewed
.\.venv\Scripts\python.exe data_pipeline/abo.py dry-run
.\.venv\Scripts\python.exe -m alembic -c apps/api/alembic.ini upgrade head
.\.venv\Scripts\python.exe data_pipeline/abo.py import
.\.venv\Scripts\python.exe scripts/index_real_images.py
# Lặp index: đúng hash/model/revision được skip, không encode lại toàn catalog.
```

`real_demo` được chọn qua DATA_PROFILE trong `.env`, rồi `docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait`. `.env` khác và credentials được giữ nguyên. `demo_seed` vẫn chọn được để chạy bài học riêng; không trộn SVG fixture vào lưới ảnh thật. PostgreSQL chung không bị reset.

## Tính đúng

Import một transaction, advisory lock; source/revision/license phải khớp. ImportBatch/raw hash/field provenance lưu riêng. Re-run dùng stable source IDs, tái sử dụng bản ghi, không ghi đè giá/kho/trạng thái operator đã thay đổi. Revision mới phải reconciliation được review, không tự ghi đè. Ảnh mới chỉ publish khi mapping/hash/decode/quyền đủ. Tìm từ khóa dùng search shadow của tên Việt + tên gốc; không có text semantic model mới và không tải model để đáp ứng hình thức.

Offline script encode512D đúng OpenCLIP revision M7, giữ content hash; chỉ ảnh approved của source approved. Bộ vector khác hash/revision bị loại; cosine exact nằm trong allowed product IDs sau hard filters. Nhiều gallery ảnh aggregate minimum cosine distance theo product, không nhân đôi kết quả. Secondary photo bị thu hồi quyền cũng không được dùng để rank.

## Phục hồi

- Download lỗi: giữ `.partial`, chạy lại cùng lệnh. Hash source đổi: dừng và review, không coi là cùng revision.
- Validate/import lỗi: transaction rollback; đọc lỗi/dry-run, sửa staging hoặc mapping rồi chạy lại. Không reset main, không `create_all`.
- Index lỗi: transaction rollback; chạy lại khi worker sẵn sàng, hash/revision bảo vệ tính tương thích. Không tính index chưa commit là coverage đạt.
- Rollback tính năng an toàn: đổi DATA_PROFILE về `demo_seed` rồi recreate API. Giữ dữ liệu/ảnh/import batches M8 cho kiểm tra, không xóa đơn.
- Downgrade0005 chủ động từ chối nếu còn real_demo hoặc nhiều gallery ảnh. Cần backup/export và quyết định xử lý dữ liệu trước; migration không xóa thêm ảnh để ép rollback. Không chạy downgrade trên main để thử.

## Kiểm và đo mới

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q --junitxml=docs/evidence/m8/pytest.xml
.\.venv\Scripts\python.exe benchmarks/scripts/m8_evaluate.py prepare
.\.venv\Scripts\python.exe benchmarks/scripts/m8_evaluate.py audit
# Chỉ chạy khi index/build đã kết thúc, không có request suy luận khác:
docker compose --env-file .env -f infra/docker-compose.yml restart api inference
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait api inference
.\.venv\Scripts\python.exe benchmarks/scripts/m8_evaluate.py cold
.\.venv\Scripts\python.exe benchmarks/scripts/m8_evaluate.py measure
.\.venv\Scripts\python.exe benchmarks/scripts/m8_browser.py
```

Qrels text là oracle cấu trúc category từ source, không human semantic judgments. Qrels ảnh dùng source product ID và ảnh khác ID/bytes không nằm trong gallery; vẫn không phải nghiên cứu ảnh điện thoại. Cache hits không được gộp vào p95 encoder mới. Số liệu M7 và reports M7 giữ riêng.

Tái tạo chính xác318 IDs bằng --reviewed và abo-selection.json. Import mới ngoài tập này bị chặn cho tới khi có review ghi lại; dry-run vẫn dùng để kiểm lỗi. Mỗi lượt benchmark lạnh cần restart cả API (xóa cache vector query trong RAM) và inference (model process mới); không xóa cache OS nên đây là process-cold. Chạy measure lặp trong TTL có thể bị guard cache-hit từ chối thay vì giả số warm inference.
