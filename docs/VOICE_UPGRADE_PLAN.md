# Cải thiện nhận giọng bằng các agent — 2026-10-23

User yêu cầu agent sửa đồng thời; đã đồng ý riêng tải PhoWhisper-base khoảng294MB (BSD-3-Clause), convert int8 và kiểm local. Giữ LOCAL_ONLY, không gửi audio ra dịch vụ, không trọng số/dataset khác ngoài đồng ý này.

- Agent ASR: sửa flush resampler, profile/model integrity, converter offline; decoder giữ cố định để so model, không lặp ba config đã thất bại.
- Agent ngữ cảnh: từ vựng public catalog, từ gần âm có anchor và xác nhận; giữ nguyên transcript/giá/màu/intent.
- Agent kiểm thử độc lập: freeze corpus/hash/split trước inference; development29 cũ và heldout29 người nói mới, không tải dataset. Chỉ chấm âm học bằng WER/CER; từ vựng/gợi ý không được tính là giảm WER.
- Agent chính: acquire official pinned snapshot + checksum/license, conversion dependency tạm, tích hợp application/domain ports, deploy có rollback và kiểm upload/quyền/UI.

CPU inference chạy tuần tự theo lượt, không chạy nhiều benchmark model cùng lúc. Gate chọn mặc định: không lỗi HTTP, primary WER heldout cải thiện và từng corpus không regression; development và regional smoke công khai riêng; đo tài nguyên cùng trạng thái model. Chưa có audio mua hàng thật/TC2, không gọi giọng đọc thành nghiệm thu voice shopping.

Model mới chỉ được chọn sau gate; base cũ vẫn trên đĩa để rollback. Không giữ hai ASR trong RAM production. Report/evidence mới dùng `docs/evidence/voice-upgrade/`, giữ số liệu lịch sử.

## Ablation tương thích sau lượt đầu

PhoWhisper official `generation_config` đặt `return_timestamps=false`, trong khi faster-whisper hiện mặc định `without_timestamps=false`. Thử đúng một thay đổi tương thích `without_timestamps=true` cho Pho trên development29; giữ các tham số khác. Tập V1 đã được mở kết quả nên mọi kiểm lại V1 chỉ là repeated validation, không gọi blind mới.

Đã freeze V2 trước ablation/quyết định config:29 utterance VIVOS mới, SHA không trùng V1,19 speaker ID có thể trùng speaker đã gặp; không đủ ViMD mới đạt1–12s. V2 chỉ kiểm unseen utterances, không phải speaker-independent hoặc smoke đủ3miền. Quyết định decoder từ cấu hình publisher và development; đo V2 cả baseline/candidate sau khóa cấu hình.

Đã khóa lựa chọn Pho `without_timestamps=true` sau development: cả WER/CER của VIVOS20 và ViMD9 tốt hơn base/Pho cấu hình đầu. `evaluation-v2-configuration-lock.json` tạo trước mọi ASR V2, gắn SHA của development evidence/manifest và flags hai model. V1 kiểm lại là repeated validation; chỉ V2 chưa được xem ở thời điểm khóa.
