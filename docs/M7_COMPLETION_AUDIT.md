# Checklist chốt M7 — 2026-10-22

## Trạng thái

Đã triển khai và kiểm thử kỹ thuật tới M7. **Chưa ghi tất cả gate đạt:** Đang chờ tệp âm thanh TC2; chưa có kết quả nghiệm thu nguyên câu từ giọng người dùng. Semantic text model, public production và P2 thanh toán/vận chuyển thật không được tuyên bố đã chạy.

| Ca | Kết quả thực tế | Bằng chứng |
|---|---|---|
| TC1 | 10 áo len đen, giá đầu264000/324000/456000, hard filters đúng | test_search.py; ui/m3-results.json |
| TC2 | ASR thật/ghi âm/sửa câu/common pipeline đã chạy; Đang chờ tệp âm thanh TC2; chưa có kết quả nghiệm thu nguyên câu từ giọng người dùng | vivos-base.json; voice-synthetic.json; ui/m5-results.json; ui/recording-results.json |
| TC3 | CLIP thật, navy sweater đầu ở fixture held-out minh họa; có benchmark đối tượng chụp độc lập | image-integration.json; ui/m4-results.json; photo-eval.json |
| TC4 | Strict1→3 sau đồng ý nới màu; đỏ95000 đầu, hai giá99000/149000 | test_course_v2.py; ui/m3-results.json; khác auto-relax slide đã ghi quyết định |
| TC5 | Owner thấy CONFIRMED/710500; anonymous/khác chủ bị chặn, không fallthrough | test_commerce.py; ui/m6-results.json; course-order.png |
| TC6 | Text/voice/image/ASR thật không đổi11 bảng nghiệp vụ; history opt-in riêng | tc6-media-readonly.json; các snapshot tests |

## Completed / Changed files

SQL repository tối ưu theo EXPLAIN, giữ quyền nguồn và composite FK; UNION chống cây danh mục giao nhau nhân đôi. Tách vector timer khỏi ranking. Thêm OnDeviceSpeech/browser-speech port, cài gói có đồng ý, local-only và timeout/cancel/fallback. BFF/form giỏ dùng chung boundedBody15s, kiểm cookie shape/qty/duplicate. Clean-start chọn cổng trống tránh Windows exclusions. Thêm HTTP Docker benchmark, VIVOS human, ảnh chụp đối tượng và warm full image path; cập nhật tài liệu/bằng chứng.

## Tests run and exact results

- verify.ps1: **127 passed/62.18s**; Ruff/format, strict mypy35 application files, Alembic check đạt (`evidence/final-verification.txt`).
- Chrome: **9/9 nhóm đạt**: e2e_storefront, e2e_text, e2e_image, e2e_voice, e2e_ondevice, e2e_recording, e2e_commerce, read_only_audit, browser_lab (`browser-final-run.json`).
- Clean Docker: migration/seed2 lần/course-v2/auth/checkout/cancel đạt (`clean-start.json`). Lượt đầu cổng3001 bị Windows chặn; đã sửa chọn cổng và chạy lại, không xóa main volume.
- BFF HTTP thật: quá bound413, cookie sai422, form no-JS hợp lệ303, chunked body không kết thúc408≈15s (`bff-upload-guards.json`).
- Callback on-device giả lập có nhãn riêng; Chrome cài gói thật nhưng probe headless chưa trả transcript. Không dùng simulation làm bằng chứng nhận dạng thật.

## Benchmarks actually measured

- 3k/204 qrels cấu trúc, HTTP Docker service p95=109.468/141.085/381.111ms tại c1/5/10, zero filter leaks. Không phải bộ human semantic judgments.
- Full image HTTP warm/không cache vector p95=429.857ms/25 ảnh. Caltech25 query khác50 gallery: recall@10=0.872, NDCG@10=0.9116; không chứng minh same-SKU/thời trang/phone.
- VIVOS20 bản ghi/10 người thật: WER=0.2392, CER=0.1200, HTTP p95=1877.518ms. Giọng đọc mẫu nhỏ, chưa đại diện ba miền/noise.

- ViMD9 nguyên trạng có nhãn3 miền +3 noise cases và2 mixed-term TTS đã đo; WER/CER/failure đều giữ trong regional-voice.json/voice-stress.json. Base còn nhận sai nhiều, không đánh dấu chất lượng cao.

## Known limitations / Next implementation task

Chạy voice_acceptance.py khi người dùng gửi tệp thật để kiểm transcript chưa sửa→winter soft→áo phao đầu. Chrome on-device còn thử nghiệm theo browser; Whisper vẫn là local adapter thật. Không tải Whisper small, không gọi API trả phí. Target tải10 còn giới hạn; cold model≈47s, không dùng cache hit giả thành inference mới. Quyền và phạm vi corpus/ảnh/giọng được ghi rõ trong BENCHMARKS/DATA_SOURCES; không gọi bản local là production.
