# Nhận giọng miễn phí và mức dùng tài nguyên

## Đang áp dụng — 2026-10-23

User đã đồng ý tải **PhoWhisper-base** chính thức VinAI, BSD-3-Clause,294MB source; CT2 int8 runtime≈80MB. Cùng cỡ74M với base cũ, CPU2threads, một ASR trong RAM; không cloud/paid API. Pho profile đặt `without_timestamps=true` theo inference config chính thức. V2 WER36,56%→7,53% trên29 utterance mới, có trùng speaker/giọng đọc; không dùng thành quality claim cho mọi giọng mua sắm. API unit157/integration187/worker20/benchmark20 và browser đạt. ASR-only RSS V2≈270MiB, sau CLIP+ASR cùng load trên worker≈1203MiB; snapshot sau request, không phải peak hoặc không tốn tài nguyên. [Báo cáo hiện tại](VOICE_UPGRADE_REPORT.md).

`.env` máy hiện chọn `ASR_MODEL_PROFILE=phowhisper-base`; `.env.example` giữ base để máy mới không tự đòi weights chưa được đồng ý. Model cũ vẫn có để rollback. Không tải Whisper small/large. Text luôn dùng được khi model thiếu/bận; không tự chuyển sang cloud.

## Quyết định lịch sử — 2026-10-22

Cập nhật 2026-10-22 theo yêu cầu ưu tiên miễn phí, ít tài nguyên. Không có phương án nhận dạng nào dùng bằng không CPU/RAM; có thể chuyển xử lý sang thiết bị hoặc nhà cung cấp. Không tải Whisper small.

| Phương án | Chi phí và tài nguyên | Trạng thái HoodooMart |
|---|---|---|
| Nhập văn bản | Không model/khóa API; chỉ parser + SQL | Mặc định ổn định, luôn có fallback |
| Web Speech trên thiết bị | Không API key hoặc phí API ứng dụng; gói Chrome tải sau đồng ý, CPU/RAM phía thiết bị | Đã thêm UI, luôn `processLocally=true`, không tự chuyển cloud. Chrome155 nhận hỗ trợ vi-VN, cài gói thành công trong hồ sơ test; nhận dạng thực tế trong headless chưa trả transcript nên còn thử nghiệm |
| Whisper base CPU cục bộ | Không phí API; weights≈145MB, CPU2 threads, model lazy trong worker chung | Chạy thật. VIVOS20 người thật/10 người nói WER23.92%, CER12%, HTTP p95≈1.88s. Không tự tải model lúc setup/query; có bước sửa câu |
| Groq Free Plan, Whisper v3 Turbo | Cần tài khoản/khóa API và Internet; audio gửi tới bên thứ ba; miễn phí trong hạn mức gói Free | Chưa kết nối/không có khóa, chưa gửi audio ra ngoài. Không coi là đã kiểm thử hoặc miễn phí vô hạn |

**Lựa chọn tại thời điểm2026-10-22:** giữ `LOCAL_ONLY=true`, thử nhận giọng trên thiết bị khi hỗ trợ; Whisper base đã có là dự phòng thật, không tải thêm model nặng. Người dùng cần kiểm tra/sửa câu trước tìm. Các API Free dưới đây chưa được kích hoạt; không gửi audio ra ngoài.

Đã đo thêm ViMD9 clips có nhãn nguồn: WER North≈50.7%, Central62.5%, South≈71.1%, chỉ3 đoạn mỗi miền. Noise và câu mua hàng tổng hợp trộn size/tiếng Anh cũng có lỗi; xem BENCHMARKS. Các kết quả này xác nhận base còn yếu trong các mẫu thử, không phải chứng nhận độ chính xác theo vùng miền. Chưa chốt TC2 trên tệp giọng thực của người dùng.

## Chrome: cài được chưa đồng nghĩa đã nhận dạng đạt

Nguồn API và danh sách ngôn ngữ: [Web Speech on-device explainer](https://github.com/WebAudio/web-speech-api/blob/main/explainers/on-device-speech-recognition.md), [cài gói ngôn ngữ](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition/install_static). Khả năng phụ thuộc browser/OS/profile; `processLocally=false` có thể dùng cloud nên ứng dụng không gọi chế độ đó.

User đã đồng ý cài gói tiếng Việt ngày 2026-10-22. Hồ sơ kiểm thử riêng nằm trong `artifacts/speech-browser`, không đọc cookie/profiles của người dùng. Quan sát file SODA runtime≈36.5MB và language model≈36.0MB, còn cache/component khác; đây là kích thước file, không phải RAM/peak. Không tái phân phối component và không gán giấy phép MIT cho gói Chrome.

`chrome-language-install.json` ghi install=true/available. Các probe độc lập `chrome-asr-probe.json`, `chrome-track-probe.json` chưa có transcript; không kết luận độ chính xác đạt từ install. UI xử lý lỗi, từ chối micro, hủy, callback đến muộn, browser không hỗ trợ và watchdog15s. `ui/ondevice-results.json` ghi rõ **callbacks giả lập**; không dùng nó làm kết quả ASR thật.

Khi dùng Chrome của bạn, mở `http://localhost:3000/search/voice`, bấm cài gói nếu được đề nghị, rồi nhận giọng. Không tự cài hoặc tự bật micro khi mở trang. Browser không hỗ trợ vẫn dùng bản ghi/Whisper hoặc text.

## Gói API miễn phí được kiểm tra, chưa sử dụng

[Groq Free Plan limits](https://console.groq.com/docs/rate-limits) hiện ghi Whisper v3/v3 Turbo: 20 request/phút, 2.000 request/ngày, 7.200 giây audio/giờ, 28.800 giây/ngày. Các giới hạn có thể đổi hoặc khác theo tổ chức; kiểm tra Limits của tài khoản. [Speech API](https://console.groq.com/docs/speech-to-text) nhận nhiều ngôn ngữ và WAV/WebM/M4A. Không dùng số WER quảng bá của nhà cung cấp làm độ chính xác tiếng Việt của ứng dụng.

Chỉ cân nhắc khi người vận hành chọn rõ gói Free và đồng ý chính sách dữ liệu. Không đăng ký billing, không tự chuyển sang dịch vụ trả phí, không đặt API key trong frontend hoặc chat. Hạn mức hết phải trả lỗi/fallback, không tự nâng gói.
