# Tìm chữ, giọng nói và ảnh ngay tại ô search

Ngày kiểm tra: **2026-10-23**. Kế hoạch: [INLINE_SEARCH_PLAN](INLINE_SEARCH_PLAN.md).

## Cách sử dụng và luồng đã tích hợp

| Đầu vào | Thao tác | Xử lý và kết quả |
|---|---|---|
| Chữ | Gõ ở header, Enter hoặc nút tìm | Mở Dialog và gọi `POST /search/text`; kết quả/phân trang ở ngay trang hiện tại. |
| Giọng nói | Bấm micro ở header | Xin quyền khi bấm, ghi trực tiếp tối đa12 giây/2MB. Dừng → tự gửi `POST /search/voice` → điền câu đã nhận. Người dùng sửa nếu cần rồi bấm Tìm; gọi cùng `/search/text` với `modality=voice`. |
| Ảnh | Bấm camera rồi chọn tệp, kéo thả hoặc Ctrl+V ảnh | Preview tạm, có xóa/thay ảnh; bấm Tìm gọi `POST /search/image`. Có thể kèm mô tả chữ/danh mục/giá tối đa. Dán ảnh trực tiếp vào ô search ở header cũng mở luồng này. |

Không đổi URL hoặc mở trang mới khi thu âm, tìm kiếm, xem kết quả hay phân trang. Chọn sản phẩm/liên kết đăng nhập vẫn điều hướng bình thường. Các đường dẫn voice/image cũ được giữ để tương thích; công cụ chính ở header/menu mở Dialog dùng chung.

Giao diện giữ một hàng nhập chữ/micro/camera/tìm, preview khi có ảnh, bộ lọc thu gọn và lưới kết quả. Có trạng thái ghi âm/nhận chữ/đang tìm, hủy, lỗi và kết quả rỗng. Đóng bằng Escape trả focus về điều khiển đã mở. Kiểm tra hình ảnh thực tế: [desktop tìm ảnh](evidence/inline-search/image-1280.png), [mobile tìm chữ](evidence/inline-search/text-390.png), [mobile ghi âm](evidence/inline-search/voice-recording-390.png).

## Logic FE và BE

- Một controller ở layout nhận sự kiện từ các ô search; không tạo nhiều recorder. Controller gắn với pathname và query string để điều hướng SPA cũng giải phóng tài nguyên.
- Khi đóng/hủy/chuyển trang: dừng recorder, nhả toàn bộ micro tracks, xóa timer, abort request, vô hiệu callback/kết quả đến trễ và revoke preview URL. Khi tab ẩn trong lúc xin quyền/ghi âm, dừng luồng ghi; quyền đến trễ được nhả ngay.
- Client abort chỉ ngừng chờ và nhận kết quả; không tuyên bố đã dừng tác vụ CPU đang chạy trên server. Worker vẫn dùng giới hạn một tác vụ, timeout/rate limits đã có.
- Không xin quyền micro khi tải trang. Trình duyệt thiếu MediaRecorder/quyền/secure context có thông báo và vẫn nhập chữ được. Không tự chuyển âm thanh sang cloud hoặc tải model.
- Ảnh JPEG/PNG/WebP tối đa5MB, audio tối đa2MB; kiểm tra client hỗ trợ UX, server vẫn kiểm kích thước/MIME/decode. Paste chỉ nhận binary image; không tự tải URL ảnh trong clipboard.
- File/preview chỉ giữ trong bộ nhớ trong luồng đang mở, không ghi raw media vào URL/localStorage/catalog. Backend nhận media tạm và giữ pipeline upload hiện có.
- Backend chuẩn hóa transcript Unicode NFC/khoảng trắng, từ chối câu rỗng hoặc quá300 ký tự. Text chỉ chứa khoảng trắng bị từ chối422. Câu sửa từ voice giữ `modality=voice` và dùng cùng bộ lọc với text.
- Kế thừa danh mục/giá tối đa hợp lệ từ trang hiện tại; hiển thị điều kiện đang áp dụng. Phân trang theo snapshot điều kiện đã tìm; không tự nới bộ lọc. Gợi ý chữ bỏ response cũ và không gửi câu vượt100 ký tự tới suggestions.
- Order intent giữ session/ownership ở server; khách chưa đăng nhập nhận401 và liên kết đăng nhập trong Dialog. API router vẫn gọi application service; không chuyển SQL vào router/domain.
- `LOCAL_ONLY=true`; dùng OpenCLIP và Whisper base CPU đã có. Không thêm API trả phí, trọng số, migration hoặc chỉnh dữ liệu catalog/đơn hàng.

## Kiểm thử đã chạy

| Lớp kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Pytest toàn backend | **183 passed trong98.10s** | [log](evidence/inline-search/pytest.txt), [JUnit](evidence/inline-search/pytest.xml) |
| Ruff check + format | Đạt;70 tệp đã đúng format trong phạm vi lệnh bên dưới | `evidence/inline-search/ruff.txt` |
| Mypy | Đạt39 source files | [log](evidence/inline-search/mypy.txt) |
| ESLint + TypeScript | Exit0 | `evidence/inline-search/eslint.txt`, `typescript.txt` (không có chẩn đoán) |
| Docker production build/up | Đạt;4 dịch vụ healthy | `artifacts/inline-search-delivery-build.log`, `evidence/inline-search/services.txt` |
| Chrome, tìm chữ responsive | Đạt360/390/768/1280/1440px, giữ URL, không tràn ngang, không tự bật micro, focus/Escape | [browser.json](evidence/inline-search/browser.json), `text-*.png` |
| Chrome, phân trang/rỗng/order auth | Đạt; khách tìm đơn nhận401 | cùng browser.json |
| Chrome, tìm ảnh thật | Picker + paste bytes qua CLIP thật; `cached=false`; xóa/revoke preview, ảnh hỏng422, quá5MB bị chặn | cùng browser.json; image-1280.png |
| Chrome, vòng đời quyền | Từ chối quyền vẫn tìm chữ; cấp quyền đến sau khi đóng được nhả | Browser instrumentation, ghi nhãn trong browser.json |
| Chrome, MediaRecorder → ASR → sửa → tìm | WebM ghi thật, Whisper trả200, điền câu; sửa thành “ghế”, giữ voice và giá tối đa; hủy/tab ẩn/SPA query navigation nhả tracks | cùng browser.json, voice-recording-390.png |

Tám test mới kiểm chuẩn hóa NFC, transcript rỗng/dài, câu text trắng và cùng kết quả/bộ lọc giữa text với câu voice đã sửa. Bộ183 test cũng chạy lại negative upload/ownership hiện có. Pytest dùng **TEST_DATABASE_URL riêng có hậu tố `_test`**, conftest chặn dùng DB khác; không reset DB chính.

Phạm vi bằng chứng trình duyệt:

- Ghi âm kiểm bằng Chrome fake microphone phát **clip giọng người thật VIVOSDEV05_155**. MediaRecorder/WebM và suy luận Whisper là thật; đây không phải micro vật lý hay TC2. Nguồn VIVOS: Luong & Vu, CC BY-NC-SA4.0, chỉ kiểm học thuật cục bộ; không phân phối audio nguồn trong evidence. JSON lưu độ dài/hash transcript.
- Clipboard được harness phát `ClipboardEvent` với bytes ảnh thật; có đi qua handler và API thật, chưa phải thao tác clipboard hệ điều hành.
- Permission denied/late grant và hidden-tab event có instrumentation để kiểm nhánh cleanup; tách khỏi bằng chứng suy luận thực.

Lỗi trong quá trình làm: ESLint báo đọc ref lúc render ở điều kiện disabled; đã chuyển sang preview state rồi chạy lại đạt. Ảnh screenshot ban đầu chụp trước khi thumbnail tải xong; harness đã chờ bốn ảnh đầu tải hoàn tất và chạy lại toàn bộ đạt. Không dùng kết quả lần lỗi để báo pass.

## Lệnh tái kiểm

Chạy ở root, tuần tự để tránh tranh CPU với inference:

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait
.\.venv\Scripts\python.exe -m ruff check apps/api scripts benchmarks/scripts/inline_search_browser.py
.\.venv\Scripts\python.exe -m ruff format --check apps/api scripts benchmarks/scripts/inline_search_browser.py
.\.venv\Scripts\python.exe -m mypy --config-file apps/api/pyproject.toml apps/api/app
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q --junitxml=docs/evidence/inline-search/pytest.xml
.\.venv\Scripts\python.exe benchmarks/scripts/inline_search_browser.py
```

ESLint/TypeScript đã chạy tại **apps/web**, dùng Node runtime có sẵn:

```powershell
$taskNode = 'C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
Push-Location apps/web
& $taskNode node_modules/eslint/bin/eslint.js src
& $taskNode node_modules/typescript/bin/tsc --noEmit
Pop-Location
```

Harness cần Chrome và hai tệp private đã có: held-out image selection trong `data/private/m8/`, VIVOS sample trong `data/private/vivos/`; không tự tải dữ liệu/trọng số thiếu. Nhật ký build nằm trong artifacts cục bộ. Không chạy công cụ xuất báo cáo M7/M8 để ghi đè bằng chứng lịch sử.

## Tệp thay đổi trong đợt này

- FE mới: `src/lib/unified-search.ts`, `src/components/unified-search.tsx`, `src/app/inline-search.css` trong apps/web.
- FE tích hợp: `search-bar.tsx`, `site-header.tsx`, `ai-navigation.tsx`, `src/lib/api.ts`, `src/app/layout.tsx`.
- BE: `apps/api/app/application/speech.py`, `apps/api/app/api/v1/search.py`.
- Test: `apps/api/tests/test_inline_search.py`, `benchmarks/scripts/inline_search_browser.py`; cập nhật assertion keyboard của `m8_browser.py` để nhận button thay link.
- Docs: README, PROGRESS, IMPLEMENTATION_PLAN, ARCHITECTURE, API_CONTRACTS, INLINE_SEARCH_PLAN và báo cáo này; bằng chứng mới dưới `docs/evidence/inline-search/`.

## Giới hạn còn lại

Whisper base có thể nhận sai tiếng Việt; người dùng được kiểm tra/sửa câu trước khi tìm. Không suy ra chất lượng đại trà hoặc cam kết độ trễ từ một clip kiểm luồng. **TC2 nguyên câu “tôi muốn mua áo mùa đông” vẫn chờ tệp âm thanh thực của người dùng**, chưa đánh dấu đạt. Không tải thêm Whisper small hay dùng dịch vụ free có cloud inference ngoài phạm vi LOCAL_ONLY.

Catalog/giá đặt thử/nguồn và giới hạn relevance giữ theo [M8 report](M8_TEST_REPORT.md) và [marketplace AI report](MARKETPLACE_AI_REPORT.md); các kết quả lịch sử được giữ nguyên, không tính thành phép đo mới của đợt này.
