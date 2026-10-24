# Search: unit test, lỗi ngữ cảnh và giới hạn ASR

Ngày 2026-10-23. Phạm vi: [SEARCH_QUALITY_PLAN](SEARCH_QUALITY_PLAN.md). Không coi unit test đạt là bằng chứng nhận giọng chính xác.

## Lỗi đã tái hiện và sửa

| Ca kiểm | Trước | Sau |
|---|---|---|
| “đèn bàn”, “đến mua tai nghe” | Có thể tạo bộ lọc màu đen sau bỏ dấu | Giữ phân biệt từ có dấu trước khi trích thuộc tính |
| “đã có tai nghe”, “năm đôi giày” | Nguy cơ da/nam bị hiểu thành thuộc tính sản phẩm | Mask từ đồng dạng có dấu; số lượng không thành giới tính nam |
| “dưới năm trăm năm mươi nghìn” | Không hiểu đầy đủ số hoặc nhận một phần | Nguyên câu tiền →550000, operator lt; VND nguyên |
| “một triệu hai trăm nghìn”, “500.000 đồng” | Cắt còn1 triệu hoặc hiểu500 |1200000 và500000 |
| “không dưới500k”, “không trên500k” | Đảo chiều hoặc thiếu cận | >=500000 và <=500000 |
| “từ200k đến500k” | Thiếu cận trên | Giữ cả200000–500000 |
| ASR “tài nghe”, “dày thể thao”, “bàng làm việc” | Chỉ có câu sai để tìm | Trả câu gốc + gợi ý cụm sản phẩm; phải chọn và bấm Tìm |
| Cảnh báo độ chắc chắn từ recognizer | FE bỏ qua, chỉ hiện thông báo chung | Hiển thị cảnh báo đã nhận ngay dưới ô search |

Không fuzzy edit giá, màu, mã đơn hay các tên đều hợp lệ như **áo lông/áo len**. Những cụm đơn quá mơ hồ như “ban”, “dày” không tự biến thành sản phẩm. Bảng gợi ý hiện có **6 cụm hữu hạn**, không phải bộ phân giải đồng âm tiếng Việt tổng quát. Câu gốc không bị thay âm thầm và ASR/gợi ý không tự gửi truy vấn. Các điều kiện UI vẫn ưu tiên cao nhất.

Ghi âm yêu cầu mono, echo cancellation, noise suppression và auto gain của trình duyệt. Khả năng hỗ trợ tùy thiết bị; chưa đo mức cải thiện âm học trên micro vật lý. Vẫn nhả tracks và bỏ kết quả đến trễ theo controller đã kiểm ở đợt trước.

## Unit test riêng, không cần DB/model

**72 backend unit tests đạt trong0.58s**; **20 frontend unit tests đạt**. Không báo phần trăm coverage vì chưa đo.

- `apps/api/unit_tests/test_query_regressions.py`: giá nói/số định dạng, số tiền không hợp lệ, từ đồng dạng, giới tính/số lượng, bất đẳng thức/khoảng giá, NFC và ưu tiên bộ lọc UI.
- `test_retrieval_contracts.py`: ranh giới < / <= / > / >= chuyển đúng trước repository; xếp hạng, hàng hết hạn mức sau hàng còn; không nới điều kiện explicit/UI; ảnh chỉ xếp hạng candidates được phép, revision đúng, ảnh không hợp lệ không gọi encoder/index. Mock repository/index là kiểm contract, không thay thế kiểm SQL/quyền thật.
- `test_speech_context.py`: giữ bản chép lời gốc, chỉ gợi ý có xác nhận; không sửa nhầm tên sản phẩm hợp lệ/intent đơn hàng; recognizer lỗi/blank/quá dài không thành câu tìm bịa.
- `apps/web/tests/search-input.test.mjs`: JPEG/PNG/WebP, đúng ranh giới5MB, tệp rỗng/MIME không hỗ trợ, ngân sách VND hợp lệ, clipboard ảnh nhị phân; URL/text clipboard không bị tải thành ảnh.

Tách `unit_tests/` khỏi conftest DB của `tests/`: chạy đơn vị offline không seed/migration hoặc cần `.env`. `testpaths` và `scripts/verify.ps1` đã bổ sung unit suite.

Đã chạy test trước khi sửa: [lượt đầu42 ca](evidence/search-quality/unit-initial-failure.txt) có14 fail/28 pass, trong đó một lỗi fixture của test ranking (tên bàn nhưng category Tai nghe) đã được sửa, không tính là lỗi ứng dụng. 13 ca còn lại tái hiện parser. Năm ca bổ sung về chiều/khoảng giá cũng fail trước sửa, log [price-direction-before](evidence/search-quality/price-direction-before.txt). Kết quả cuối [unit.txt](evidence/search-quality/unit.txt), [unit.xml](evidence/search-quality/unit.xml), [frontend-unit.txt](evidence/search-quality/frontend-unit.txt).

## Integration, build và trình duyệt

- **187 backend integration tests đạt trong46.84s**, [log](evidence/search-quality/integration.txt), [JUnit](evidence/search-quality/integration.xml). Có bốn test mới kiểm giá nói đến SQL/catalog và schema voice giữ original/suggestions. Test schema dùng recognizer giả có nhãn; không tính thành đo ASR.
- DB dùng `TEST_DATABASE_URL` riêng hậu tố `_test`, conftest chặn DB khác; upload/ownership negative suite hiện có chạy lại. Không reset DB chính, không đổi schema/quyền dữ liệu.
- Ruff đạt; mypy40 source files đạt; ESLint/TypeScript exit0. Log tại `evidence/search-quality/ruff.txt`, `mypy.txt`, `eslint.txt`, `typescript.txt`.
- Production Docker build/up đạt; log cục bộ `artifacts/search-quality-final-build.log`. Dịch vụ và UI theo bằng chứng nghiệm thu runtime mới trong `evidence/search-quality/`.
- [suggestion-browser.json](evidence/search-quality/suggestion-browser.json):390/1280px, recognizer response được giả lập rõ ràng; nguyên câu và warning hiện, chưa có request tìm trước xác nhận, câu chọn đi qua **BFF/text retrieval thật**, giữ voice/giá/URL. [Ảnh mobile](evidence/search-quality/voice-suggestion-390.png) là ca fixture, không phải câu nhận từ micro vật lý.
- [Bộ Chrome search tại chỗ](evidence/search-quality/inline-regression/browser.json) chạy lại đạt: chữ5 viewport, ảnh/CLIP thật, paste event có bytes thật, lỗi tệp/quyền và actual MediaRecorder → Whisper. Đầu vào là Chrome fake microphone phát VIVOS; không phải TC2/micro vật lý.
- Lượt harness đầu gặp CSP do `wait_for_function` nhận chuỗi expression; đã đổi thành hàm arrow và chạy lại. **Không nới CSP của ứng dụng**; giữ log `inline-harness-csp-failure.txt`.

## Thử thay đổi decoder: kết quả không đủ để triển khai

Baseline mới dùng cùng20 clip giọng người thật VIVOS đã có, thêm7 clip eSpeak cùng một câu mua sắm. SHA256 từng audio tại [asr-before.json](evidence/search-quality/asr-before.json). Không tải dữ liệu/weights. VIVOS của Luong & Vu, CC-BY-NC-SA4.0, dùng học thuật cục bộ; không phân phối audio nguồn.

| Cấu hình | WER20 clip đọc thật | WER7 clip tổng hợp mua sắm |
|---|---:|---:|
| Hiện tại, Whisper base int8 |0.2392|0.8095|
| Prompt danh mục sản phẩm |0.2727|0.6905|
| Prompt mua sắm ngắn |0.2536|0.7143|
| Beam5, bỏ repetition/ngram penalties |0.2344|1.6190|

**Không cấu hình nào cải thiện cả hai nhóm; không đưa các thử nghiệm này vào decoder production.** Bằng chứng: [asr-experiments.json](evidence/search-quality/asr-experiments.json) và ba candidate JSON/summary cùng thư mục. Cấu hình tái tạo trong `benchmarks/scripts/search_voice_policies.py`; chỉ dùng benchmark. Tham số đối chiếu từ [mã nguồn faster-whisper1.2.1](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/transcribe.py).

Sau build cuối đã gọi lại API cho đúng27 tệp, tất cả HTTP200, SHA256 khớp baseline: [asr-after.json](evidence/search-quality/asr-after.json). WER hai nhóm **không đổi** (0.2392/0.8095). Bản sửa logic/gợi ý không được diễn giải thành cải thiện âm học. Không dùng chênh timing của hai lượt để kết luận tăng tốc.

WER có thể vượt1 vì từ chèn thêm; bộ chuẩn hóa giữ cách nói số/chữ số khác nhau nên cũng tính là lỗi.20 clip là giọng đọc chung, không chứng minh nhận đúng tên sản phẩm/tiếng địa phương/giọng nói mua sắm.7 clip tổng hợp cùng câu không phải7 ý định/người nói thật. Không dùng latency thử nghiệm trong worker riêng để cam kết hiệu năng HTTP; một lượt thử chạy cùng integration nên timing không dùng làm benchmark.

## Lệnh đã chạy / tái kiểm

```powershell
# Unit offline, độc lập DB/model:
.\.venv\Scripts\python.exe -m pytest apps/api/unit_tests -q --junitxml=docs/evidence/search-quality/unit.xml
$taskNode = 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
Push-Location apps/web
& $taskNode --test tests/search-input.test.mjs
& $taskNode node_modules/eslint/bin/eslint.js src tests
& $taskNode node_modules/typescript/bin/tsc --noEmit
Pop-Location
.\.venv\Scripts\python.exe -m mypy --config-file apps/api/pyproject.toml apps/api/app
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q --junitxml=docs/evidence/search-quality/integration.xml
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait api web
.\.venv\Scripts\python.exe benchmarks/scripts/search_quality_browser.py
$env:INLINE_SEARCH_EVIDENCE='docs/evidence/search-quality/inline-regression'
.\.venv\Scripts\python.exe benchmarks/scripts/inline_search_browser.py
# Chạy ASR tuần tự khi inference không bận; không tự tải dữ liệu thiếu:
.\.venv\Scripts\python.exe benchmarks/scripts/search_voice_compare.py before
# Sau sửa/build, cùng SHA256 audio; before sẽ bị ghi lại nếu chạy lệnh trên:
.\.venv\Scripts\python.exe benchmarks/scripts/search_voice_compare.py after
```

ASR candidate harness chạy trong inference container với bản sao WAV private dưới `/tmp`, `PYTHONPATH=/worker`; copy `search_voice_candidate.py` + `search_voice_policies.py` vào cùng thư mục rồi truyền `directory policy` (`long_prompt`, `short_prompt`, `beam5`). Không cung cấp endpoint thử nghiệm trên web. Tạo baseline mới vào thư mục riêng nếu cần giữ snapshot nghiệm thu.

## Giới hạn cần giữ rõ

Whisper base hiện vẫn có lỗi nghe; bản sửa này xử lý các lỗi parser và hỗ trợ xác nhận một số cụm gần âm, **chưa giải quyết triệt để chất lượng mô hình âm học**. Cần corpus giọng người thật nói tên/giá sản phẩm với đáp án để đo đúng vấn đề người dùng nêu; không lấy unit test giả lập làm chứng nhận ASR. TC2 nguyên câu vẫn chưa có file thật. Giữ `LOCAL_ONLY=true`, không model mới/API ngoài/giá hoặc review bịa, không đổi nguồn public catalog.

Tệp chính thay đổi: query_parser, speech_context/SpeechService/Transcript/API schema; shared search-input và Dialog/ô search; unit/integration/browser/ASR benchmark scripts; OpenAPI + TS schema; test commands và tài liệu. Backend routers vẫn gọi application services, không kéo SQL vào domain/application.
