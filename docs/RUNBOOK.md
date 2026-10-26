# Vận hành — PowerShell 7

Chạy ở thư mục gốc `D:\PTTKHT WEB ecommerce`. Docker Desktop Linux engine. Docker là đường chạy đầy đủ; native tools cần Python3.12/3.13 và frontend Node24. Không đọc/in `.env` vào log.

## Khởi động và dữ liệu

```powershell
.\scripts\setup.ps1
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait
docker compose --env-file .env -f infra/docker-compose.yml exec -T api alembic upgrade head
docker compose --env-file .env -f infra/docker-compose.yml exec -T api python -m app.infrastructure.seed
docker compose --env-file .env -f infra/docker-compose.yml exec -T api python -m app.infrastructure.course_fixture
Invoke-RestMethod http://localhost:8000/health/ready
```

Mở localhost:3000 (API docs8000). Host ports: DB55432, API8000, web3000, worker19090. Windows loại trừ port9000 nên worker host dùng19090; nội bộ9000. Đổi WEB_PORT/API_PORT trong Compose tự đổi Origin allowlist; health check gửi external Host hợp lệ bằng Node http. BFF không so Origin với hostname0.0.0.0 nội bộ Docker.

Seed additive, raw drift bị từ chối; course-v2 lặp an toàn nhưng sẽ dừng nếu offer không còn đúng phiên bản mong đợi. DATA_PROFILE=approved_public không công khai fixture demo. Setup tạo secret ngẫu nhiên khi chưa có `.env`, không ghi đè file có sẵn.

## Trọng số và chỉ mục ảnh

Đã có consent cho OpenCLIP≈605MB + Whisper base≈145MB; CPU libraries/container tải thêm, tổng vài GB đĩa. Trọng số pinned repo/revision/SHA256/MIT ở `docs/evidence/model-manifest.json`. Chỉ chạy download khi đã đồng ý; setup/compose không tự tải model. Máy hiện tại đã có weights.

```powershell
.\.venv\Scripts\python.exe scripts/download_models.py
.\.venv\Scripts\python.exe scripts/index_images.py
Invoke-RestMethod http://localhost:19090/health
```

Index chạy offline cho products published/rights-safe, kiểm source image hash, dùng đúng CLIP revision. Sau admin publish mới, chạy index lại. Không encode toàn gallery trong mỗi query. Models mount read-only; lazy load lúc request đầu. Health phân biệt file có và model đã load; thiếu model vẫn dùng text, media trả503/fallback. Không thay weights cùng tên rồi giả metadata revision cũ.

## Tài khoản, vai trò và đơn mẫu

```powershell
.\.venv\Scripts\python.exe scripts/provision_account.py --email ban@example.invalid --role customer --bind-fixture-order
.\.venv\Scripts\python.exe scripts/provision_account.py --email quantri@example.invalid --role admin
.\.venv\Scripts\python.exe scripts/provision_account.py --email nguoiban@example.invalid --role seller
```

Password getpass, không argv/stdout/default credential. Existing account được đổi password rõ ràng bằng lệnh operator này; role seller tạo approved demo profile. Gán đơn20261005 chỉ khi owner là disabled fixture hoặc cùng user; nếu đã thuộc người khác, từ chối. Đăng nhập UI rồi `/account/orders`, `/orders/lookup` hoặc câu `kiểm tra đơn hàng 20261005`. Cấp admin xong vào `/manage`. Không dùng dữ liệu cá nhân thật trong demo.

## Nhập danh mục

UI quản lý chọn ảnh đã duyệt; import JSON chỉ admin, max20, bấm preview rồi confirm tạo draft. Mỗi bản ghi có source/raw hash/batch; exact body lặp tái dùng bản ghi dưới khóa user, không nhân đôi. Publish tách riêng sau review. Ví dụ JSON (thay image_id bằng ID từ `GET /api/v1/manage/images`):

```json
[{"name":"Áo len mô phỏng mới","description":"Mô tả nguyên bản do người vận hành tạo","category_id":"ao-len-nam","image_id":"THAY_BANG_ID_ANH_DA_DUYET","price_vnd":200000,"stock":8,"color":"đen","material":"len","size":"M","original_data_confirmed":true}]
```

Không arbitrary image URL, không public unknown-rights, không coi imported source price là giá merchant thật. Bản này chỉ hỗ trợ demo original; source adapter ngoài cần quyền và quarantine riêng.

## Kiểm thử và hợp đồng

```powershell
.\scripts\verify.ps1
.\scripts\verify-clean.ps1
.\.venv\Scripts\python.exe data_pipeline/audit.py --output docs/evidence/dataset-audit.json
.\.venv\Scripts\python.exe scripts/export_openapi.py
```

verify: Ruff/format/strict mypy/Alembic check/test DB/pytest. TEST_DATABASE_URL phải kết thúc `_test`; chỉ DB đó bị down/up và seed. Không chạy đồng thời pytest và scale_eval vì dùng cùng test DB. verify-clean tạo project/volume riêng, tự chọn4 cổng loopback trống qua OS để tránh dải bị Windows loại trừ; cổng thực được ghi trong clean-start.json. Full stack, repeat seed+course-v2, BFF auth/checkout/cancel rồi dọn project đó; không chạm volume main và khôi phục biến môi trường trước khi chạy.

Frontend native (Node24 có sẵn trong runtime Codex của máy này; máy khác cài Node24 hoặc dùng Docker):

```powershell
$taskNode='C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
.\.venv\Scripts\python.exe scripts/export_openapi.py
Push-Location apps/web
& $taskNode node_modules/openapi-typescript/bin/cli.js ../../docs/openapi.json -o src/lib/schema.ts
& $taskNode node_modules/eslint/bin/eslint.js src
& $taskNode node_modules/next/dist/bin/next build
Pop-Location
# Chỉ dùng native web khi đã stop service web để trống3000:
docker compose --env-file .env -f infra/docker-compose.yml stop web
.\scripts\start-web.ps1
.\scripts\stop-web.ps1
```

Fresh native node_modules: chạy npm ci bằng npm CLI dưới Node24 tại apps/web (không dùng wrapper npm.ps1 trỏ Node22 cũ của máy này). Docker build tự npm ci đúng Node24.13.0. OpenAPI types là generated, không sửa tay.

Native API: giữ PostgreSQL, stop API container để trống8000; root `.env` đọc host DB55432.

```powershell
docker compose --env-file .env -f infra/docker-compose.yml stop api
.\.venv\Scripts\python.exe -m alembic -c apps/api/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

## Chrome và benchmark thật

Chrome đã cài; Python Playwright nằm trong dev dependencies. Các script dùng channel chrome headless, không cần tự tải Chromium. Chạy stack đầy đủ trước:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_storefront.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_text.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_image.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_voice.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_ondevice.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_recording.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_commerce.py
.\.venv\Scripts\python.exe benchmarks/scripts/read_only_audit.py
.\.venv\Scripts\python.exe benchmarks/scripts/browser_lab.py
.\.venv\Scripts\python.exe benchmarks/scripts/scale_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/text_benchmark.py
.\.venv\Scripts\python.exe benchmarks/scripts/image_integration.py
.\.venv\Scripts\python.exe benchmarks/scripts/voice_integration.py
.\.venv\Scripts\python.exe benchmarks/scripts/voice_synthetic_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/fashion_mnist_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/photo_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/warm_image_api.py
.\.venv\Scripts\python.exe benchmarks/scripts/vivos_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/regional_voice_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/voice_stress_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/bff_guards.py
.\scripts\benchmark-http.ps1
# Khi người dùng thực sự gửi tệp âm thanh:
.\.venv\Scripts\python.exe benchmarks/scripts/voice_acceptance.py 'D:\duong-dan\ban-ghi.wav'
```

E2E commerce tạo account browser ngẫu nhiên, setup owner fixture có guard, restore owner bằng atexit; tạo order mới rồi cancel, không thu tiền. Không log password. Recording test là fake audio device + real recorder/ASR, không micro vật lý. ASR synthetic và Fashion-MNIST có nguồn/giới hạn riêng tại DATA_SOURCES/BENCHMARKS. Scale tạo2950 row run-scoped trong `_test` và xóa exact IDs trong finally, không reset main. Đọc kết quả thật, không coi script exit là chứng minh chất lượng người dùng.

Benchmark dữ liệu ngoài là lệnh chủ động, không chạy trong setup/app: VIVOS tải≈85MB; Caltech≈137MB; ViMD lần đầu≈463MB một shard, rồi tái dùng9 WAV private có kiểm SHA256. ViMD không tái phân phối/cắt audio; noise derivative chỉ dùng VIVOS cho phép share-alike. Tất cả nằm data/private, không tự publish vào catalog. API dataset có thể đổi/lỗi; ghi lỗi, không giả metrics khi chưa có dữ liệu.

## Quan sát, lỗi và dừng

```powershell
docker compose --env-file .env -f infra/docker-compose.yml ps
docker compose --env-file .env -f infra/docker-compose.yml logs --tail 20 api inference web
docker stats --no-stream
docker compose --env-file .env -f infra/docker-compose.yml stop
```

DB fail: xem migrate/ready và secret khớp volume, không xóa volume. 503 model: kiểm file/manifest/worker health; 429 đợi worker rảnh; text vẫn là fallback. Port conflict: kiểm process sở hữu và `netsh interface ipv4 show excludedportrange protocol=tcp` trước khi đổi. Cổng clean3001 bị Windows loại trừ trong lần chạy2026-10-22; script nay chọn động và đã chạy lại. Không bật native web và Docker web cùng3000.

Schema main không down/base tự động; downgrade có thể bị chặn để bảo vệ dữ liệu deep category/shared image key. Backup trước sửa schema; backup/restore production chưa được nghiệm thu. Public TLS, Secure cookies, migration/API role separation và host/origin khác cần cấu hình/kiểm thử mới, không mở host0.0.0.0 từ bản local rồi gọi production-ready.

Mã backend từ 2026-10-25 yêu cầu revision `0006_search_trace` để readiness đạt.
Migration thêm metadata lịch sử opt-in; không cần seed lại. Backup trước khi upgrade;
downgrade về `0005_real_catalog` làm mất các cột/bảng metadata mới. Xem
[đối chiếu thiết kế và bằng chứng kiểm thử](BACKEND_DESIGN_ALIGNMENT.md).


## Danh mục hiện tại — 2026-10-26

Head hiện tại là `0007_menswear_categories`; các ghi chú 0006 ở trên là lịch sử.
Catalog chỉ hiển thị cây thời trang nam mới (23 nút, 19 mục lá); danh mục cũ vẫn giữ nhưng tắt.
Không seed/import lại dữ liệu cũ để thay thế catalog mới. ID lá, backup và hướng dẫn rollback có guard tại
[MENSWEAR_CATEGORIES](MENSWEAR_CATEGORIES.md). Chưa có sản phẩm thời trang mới được nhập.


## Cập nhật máy hiện tại — 2026-10-26

PostgreSQL host dùng localhost:15432 (.env), thay55432 vì Windows đang loại trừ cổng cũ.
DATABASE_URL/TEST_DATABASE_URL đã đồng bộ; DB và password không đổi. DATA_PROFILE=real_demo,
catalog có một mẫu Rhodi đã duyệt với ảnh URL trực tiếp. Lệnh docker compose phải có --env-file .env.
Xem [SHOP_SAMPLE_PREVIEW](SHOP_SAMPLE_PREVIEW.md) cho import, nguồn, backup và bằng chứng render.
