# Search tại chỗ — 2026-10-23

- Một bộ điều khiển trong layout, dùng Dialog hiện có. Mọi ô search gọi cùng bộ điều khiển; không tạo recorder riêng ở từng ô. Trang nền/URL được giữ nguyên đến khi người dùng chọn một sản phẩm hoặc liên kết điều hướng.
- Text: Enter/nút tìm → POST search/text, kể cả order intent đã được bảo vệ ownership. Gợi ý bỏ kết quả cũ khi query thay đổi, không gọi API suggestion với q vượt100 ký tự.
- Voice: thao tác micro → getUserMedia → MediaRecorder≤12s/2MB → tự POST search/voice khi dừng → câu sửa≤300 ký tự → cùng POST search/text modality voice. Không tự xin quyền khi tải trang, không dùng cloud hoặc cài model. Hủy/đóng/chuyển trang nhả tracks, dừng timer, hủy request và vô hiệu kết quả đến trễ.
- Image: chọn JPEG/PNG/WebP≤5MB, kéo thả hoặc paste binary image vào ô search/modal; không tự fetch URL ảnh từ clipboard. Preview tạm, có xóa/thay ảnh. Ảnh + câu chữ + danh mục/ngân sách đi cùng POST search/image. Không persist raw media vào URL/localStorage/DB.
- Kết quả tại chỗ có loading/error/empty, phân trang theo snapshot điều kiện đã tìm, link sang sản phẩm. Điều kiện nhập được giữ cứng; không tự nới. Đăng nhập/đơn vẫn kiểm bằng session server.
- Backend chuẩn hóa bản chép lời NFC/khoảng trắng, giới hạn câu300 đồng nhất với text search; từ chối text chỉ có khoảng trắng. Giữ upload limits, MIME/decode, local inference, rate/deadline và separate test DB.
- Kiểm Chrome bằng MediaRecorder/ASR thật với microphone đầu vào phát tệp test có nhãn mô phỏng. Tách test permission denied/late grant/cancel/stale response bằng browser instrumentation khỏi suy luận thật. TC2 vẫn chờ audio người dùng, không gọi clip VIVOS/TTS là TC2.
