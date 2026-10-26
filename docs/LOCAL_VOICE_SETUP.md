# Nhận giọng cục bộ trên máy hiện tại — 2026-10-26

## Sửa lỗi từ chối bản ghi nhỏ — 2026-10-26

Log thực tế có nhiều `/transcribe` trả 422. Thông báo người dùng chụp xuất phát
từ `audio_decode.py`, trước bước chạy model: cổng cũ xét năng lượng trung bình
của toàn bản ghi dưới `1e-6`. Câu ngắn, âm nhỏ và khoảng lặng có thể bị loại.
Chưa có bản ghi micro vật lý để khẳng định nguyên nhân thiết bị của người dùng.

Đã xét năng lượng theo cửa sổ 100 ms, giữ chặn im lặng/nhiễu lượng tử, tăng âm
bản ghi nhỏ tối đa 20 lần. Tách lỗi bản ghi quá ngắn với lỗi không có tín hiệu.
Hai giao diện voice dùng chung bộ chọn micro và thanh mức âm; sau 2 giây không
có tín hiệu, hướng dẫn kiểm tra nút tắt tiếng hoặc dừng/chọn micro khác. Bộ đo
không phát tiếng ra loa và đóng AudioContext khi dừng/hủy/đóng giao diện.
Không lưu bản ghi người dùng, không thêm model hoặc dependency.

Đã chạy:

- Worker `python -m unittest discover -s /tests -q` trong Docker `--network none`,
  mount decoder và tests hiện tại: **22 tests đạt** (thêm bản ghi nhỏ kèm khoảng
  lặng và nhiễu gần im lặng).
- Ruff decoder/tests, ESLint ba component đã sửa, Docker build inference/web
  (gồm TypeScript), `git diff --check`: đạt.
- `node --test tests/search-input.test.mjs`: **20 tests đạt**; Node có cảnh báo
  MODULE_TYPELESS_PACKAGE_JSON, không có test lỗi.
- `artifacts/backend-check-env/Scripts/python.exe artifacts/verify_microphone_fix.py`:
  WAV eSpeak giảm âm 500 lần, thêm lặng tới 12 giây, chứng minh năng lượng thấp
  hơn ngưỡng cũ và được PhoWhisper thật nhận ra. Chrome micro mô phỏng im lặng:
  bộ đo/cảnh báo hiện, backend trả lỗi đúng, chọn micro áp dụng deviceId,
  hủy nhả tracks, vẫn tìm được bằng chữ. Evidence `artifacts/microphone-fix.json/png`.
- Chạy lại `artifacts/verify_local_voice_real.py`: MediaRecorder/WebM tới model
  thật, sửa câu trước khi tìm và nhả micro đạt.
- `docker compose --env-file .env -f infra/docker-compose.yml up -d --no-deps --wait inference web`:
  hai dịch vụ healthy với bản sửa.

Chưa thử micro vật lý hoặc đo chất lượng nhận dạng giọng người dùng. Không cần
thay database; không chạy lại toàn bộ backend integration suite cho sửa decoder/UI này.

## Thiết lập ban đầu

Theo lựa chọn cuối của người dùng, không tích hợp Google Cloud Speech-to-Text.
Đã gỡ SDK vừa cài cho phương án bị hủy; không thêm dependency Google vào project,
không sửa cấu hình xác thực và không gọi Google API. `LOCAL_ONLY=true` được giữ.

Máy này ban đầu có faster-whisper trong worker nhưng thư mục models trống;
Chrome chỉ có gói SODA en-US. Sau khi người dùng đồng ý tải một model cục bộ,
đã tải PhoWhisper-base từ VinAI, kiểm SHA256 checkpoint và giấy phép rồi chuyển
int8 bằng converter có sẵn trong repo. Chỉ tải model nhận giọng, không tải CLIP,
dataset hoặc các model khác.

Nguồn: [VinAI/PhoWhisper-base tại revision đã ghim](https://huggingface.co/vinai/PhoWhisper-base/tree/7ebdb9e88f5cc5271fb88f4d642c82ff9388650e).
Giấy phép BSD-3-Clause được giữ cùng model. Checkpoint SHA256:
`910b9e8875497078efa83dc506ea7ee378e4e759a206ceecbf23e088aec9b9f8`.

## Luồng sử dụng

Nhấn micro ở ô tìm kiếm, nói và dừng ghi. faster-whisper/PhoWhisper xử lý trên
CPU của worker cục bộ. Câu nhận được hiện trong ô có thể sửa; chỉ khi bấm Tìm
mới gửi câu đã sửa sang pipeline tìm sản phẩm. Không tự sửa số tiền, màu, size
hay tự tìm bằng transcript chưa được người dùng xác nhận.

Giới hạn và kiểm tra âm thanh đang có được giữ nguyên: 2 MB/15 giây, tệp hợp lệ,
không video/hỏng/silence, không lưu raw audio; dừng/hủy/đóng sẽ nhả micro.
Không tạo thêm luồng search, adapter cloud hoặc abstraction không cần thiết.

## Cấu hình và tệp

- `.env`: `ASR_MODEL_PROFILE=phowhisper-base`; các credentials/DB/profile khác giữ nguyên.
- Checkpoint gốc: `models/phowhisper-base-source/` và `acquisition.json`.
- Runtime: `models/phowhisper-base-int8/`, kèm `conversion-manifest.json`.
  Model được kiểm hash trước load; weights mount read-only trong worker.
- `scripts/download_phowhisper.py --consent`: CLI tải riêng model này khi có đồng ý.
  Không được gọi từ setup hay startup; không ghi đè model có hash không đúng.
- Converter dùng dependencies tạm trong container tự xóa; requirements/runtime
  production không thay đổi. Không đưa models hoặc .env lên Git.

## Lệnh và kết quả thực tế

```powershell
artifacts/backend-check-env/Scripts/python.exe scripts/download_phowhisper.py --consent
# Container tạm dùng image hoodoomart-inference, mount models ghi được và converter
# apps/inference/convert_phowhisper.py read-only. Script: artifacts/convert-local-asr.sh.
docker compose --env-file .env -f infra/docker-compose.yml up -d --no-deps --wait inference
docker compose --env-file .env -f infra/docker-compose.yml build web
docker compose --env-file .env -f infra/docker-compose.yml up -d --no-deps --wait web
$env:PYTHONPATH='apps/api'
artifacts/backend-check-env/Scripts/python.exe -m pytest apps/api/unit_tests/test_phowhisper_download.py apps/api/unit_tests/test_local_speech_adapter.py apps/api/unit_tests/test_speech_context.py apps/api/unit_tests/test_speech_catalog_service.py apps/api/tests/test_speech.py apps/api/tests/test_media.py apps/api/tests/test_commerce.py -q --tb=short -p no:cacheprovider --junitxml=artifacts/local-voice-tests.xml
artifacts/backend-check-env/Scripts/python.exe -u artifacts/verify_local_voice_real.py
```

137 tests đạt/25.37s trên TEST_DATABASE_URL riêng tới hoodoomart_test;
Ruff đạt; web build/TypeScript đạt. Worker unittest chạy trong image hiện có,
mount apps/inference/tests vào /tests, `--network none`, đạt 20 tests/0.303s.

Chrome thực tế dùng thiết bị micro mô phỏng phát WAV eSpeak có sẵn, qua
MediaRecorder/WebM → API → PhoWhisper int8 thật. Xác nhận không tự search,
sửa transcript thành `áo pull đen`, gửi đúng câu/modality=voice, nhận sản phẩm
và nhả mọi audio track. Evidence: `artifacts/local-voice-real.json` và
`artifacts/local-voice-real.png`. Harness UI stub trước đó được ghi riêng tại
`artifacts/local-voice-edit.json`, không dùng làm kết quả chất lượng ASR.
Health sau request xác nhận asr_files=true, asr_loaded=true, profile phowhisper-base.

Lượt converter đầu thiếu requests/certifi do khác phiên bản Hub giữa môi trường
hiện tại và converter cũ. Đã bổ sung dependencies vào thư mục tạm của container
chuyển đổi; converter sau đó thành công. Không tải lại checkpoint, không cài
các dependencies chuyển đổi vào worker production.

Chưa kiểm micro vật lý, giọng người dùng hoặc đo WER mới. Không dùng kết quả
eSpeak này để khẳng định nhận đúng mọi giọng nói. Không đổi schema/giá/đơn/kho,
không seed database chính; model ảnh vẫn ngoài phạm vi lần này.
