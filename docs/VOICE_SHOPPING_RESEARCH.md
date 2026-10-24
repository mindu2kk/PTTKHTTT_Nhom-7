# Voice shopping: hiểu đúng ý và tìm đúng sản phẩm

Ngày rà soát: **2026-10-24**. Đây là nghiên cứu và audit mã hiện tại; chưa thay decoder, worker, API hoặc chạy thêm suy luận. Không tải weights/dataset. Mục tiêu người dùng: ít nhất70% **câu nói tìm hàng** được hiểu đúng ý và trả sản phẩm phù hợp, gồm danh mục, màu và giá khi được nói rõ.

## 1. Đo kết quả người mua cần

WER/CER giúp xác định lỗi nghe nhưng chưa trả lời câu hỏi tìm đúng hàng. Chẳng hạn, sai một từ đệm có thể không đổi kết quả; bỏ từ “không” hoặc nghe550 nghìn thành50 nghìn có thể đổi hoàn toàn yêu cầu. Nghiên cứu [SLURP, EMNLP2020](https://aclanthology.org/2020.emnlp-main.588/) cũng phân biệt suy luận ý định/thực thể từ speech và đánh giá lỗi thực thể của pipeline. Không sử dụng dataset tiếng Anh đó để chứng nhận tiếng Việt của dự án.

Đề xuất khóa oracle trước khi sửa logic:

- Mỗi câu có `intent`, nhóm sản phẩm/danh mục chấp nhận được, bộ lọc bắt buộc và tập sản phẩm phù hợp đã duyệt từ catalog snapshot.
- **Một câu đạt first-pass** khi ASR→parser→retrieval nhận đúng intent, giữ đúng tất cả điều kiện được nói rõ và có ít nhất một sản phẩm phù hợp trongTop3. Các sản phẩm hiển thị không được vi phạm giá/màu/danh mục cứng. Quy tắcTop3 phải khóa trước khi đo, không đổi sangTop10 để nâng điểm.
- Câu có yêu cầu không thể đáp ứng chỉ đạt nếu báo không có hàng phù hợp hoặc xin làm rõ đúng lý do; không tính việc đưa sản phẩm gần giống ngoài điều kiện là thành công.
- Báo riêng **assisted success** sau khi người dùng chọn gợi ý/sửa câu. Không gộp assisted vào first-pass hoặc lấy một câu text gõ đúng thay cho audio.
- Báo thêm intent accuracy, category accuracy, exact critical-slot accuracy, relevant-product hit@3, tỷ lệ yêu cầu làm rõ, lỗi đổi điều kiện cứng và latency. Tổng tỷ lệ thành công được chấm theo câu, không lấy trung bình các tỷ lệ thành phần.

Với100 câu text có oracle, kết quả chỉ chứng minh phần parser/retrieval. Để kết luận70% **câu nói**, chính các case có audio thật phải đi qua MediaRecorder hoặc API speech thật rồi đến kết quả sản phẩm. Audio tổng hợp, VIVOS/ViMD giọng đọc chung, unit fixture và manual transcript đều phải báo riêng. VIVOS/ViMD hiện có phù hợp hồi quy ASR phổ thông, không có nhãn ý định mua sắm/giá/màu để chứng nhận mục tiêu mới.

## 2. Audit hiện trạng

| Tầng | Mã hiện tại | Hệ quả và hướng sửa cần kiểm |
|---|---|---|
| Thu âm | `unified-search.tsx`: mono, echo cancellation/noise suppression/auto gain; WAV/WebM/Ogg/MP4 tùy trình duyệt; dừng/hủy nhả tracks | Đã có luồng thu âm tại chỗ. Chưa có bằng chứng chất lượng micro vật lý; các constraint là yêu cầu gửi trình duyệt, không bảo đảm thiết bị áp dụng |
| ASR | PhoWhisper-base int8, `language=vi`, `without_timestamps=True`,2 CPU threads, một job; giữ base cũ để rollback | Giữ cấu hình đã đo và quyền local. Báo cáo trước tại [VOICE_UPGRADE_REPORT](VOICE_UPGRADE_REPORT.md) đo giọng đọc, chưa đo ý định mua hàng |
| Ngữ cảnh | `SpeechService` gọi recognizer trước, sau đó mới đọc catalog public;6 cặp gần âm cũ và tối đa256 cụm/3 gợi ý | Đây là **gợi ý sau ASR**, chưa phải context bias trong decoder. Không tuyên bố model đã nghe theo danh mục |
| Từ vựng | `speech_context.py`: chỉ public verified có nguồn/quyền ảnh; cụm2–6 từ; tên có proper-name suffix bị bỏ; có anchor/ngữ cảnh mua sắm | Bảo toàn provenance nhưng loại các tên một từ và nhiều brand/model. Các câu “cần một chiếc…”, “cho mình xem…” có thể không kích hoạt `SHOPPING_CUE` hiện tại. Cần đo coverage trước khi mở rộng |
| Parser | Tên danh mục đầy đủ/alias hữu hạn; chọn một category dài nhất; regex giá/màu/chất liệu/giới tính | Câu đa ý, phủ định và lời nói thông thường cần kiểm riêng. Không tự đổi câu đa sản phẩm thành một category vì category đó có nhiều hàng |
| Retrieval/ranking | Hard filters trước truy vấn; ranking dùng normalized utterance, stop words hữu hạn, ngưỡng lexical0.4; category match có relevance floor0.85 | Câu nghe đúng vẫn có thể tìm yếu do từ đệm/từ số tham gia denominator hoặc category quá rộng. Sửa ở lexical representation có thể rẻ và hiệu quả hơn chạy ASR lần hai |

Điểm cần lưu ý: ngữ cảnh public hiện chỉ318 sản phẩm theo báo cáo trước, không phải tất cả hàng thường được hỏi. Giá/kho là mô phỏng. Không thay nguồn hàng hoặc bịa giá, màu, tên SKU nhằm làm benchmark thành công.

## 3. Các hướng dùng model đã có

### Ưu tiên1: sửa phần hiểu câu, giữ nguyên audio và ASR

Sau baseline100 oracle text, phân loại lỗi thành nghe sai / intent sai / slot sai / ranking sai / catalog không có hàng. Nếu text đúng cũng thất bại thì sửa parser/retrieval trước:

1. Tạo trường lexical terms riêng từ cùng bản câu gốc; loại span số tiền/operator đã parse và từ đệm đã duyệt khỏi tín hiệu xếp hạng. Giữ bản gốc để hiển thị và giữ hard slots đầy đủ. Không strip số mù quáng khỏi model/SKU/size.
2. Bổ sung alias tên nhóm hàng từ category public và alias được review, thử cả cách gọi ngắn/thường nói. Không biến một tên hàng hợp lệ thành loại khác chỉ vì catalog đang thiếu hàng đó.
3. Nhận diện phủ định/điều kiện mâu thuẫn: “không màu đen”, “không quá…”, “trừ…”, “bàn hoặc ghế”. Nếu parser chưa thể biểu diễn chính xác thì xin làm rõ; không im lặng bỏ phủ định hoặc chọn một nhánh.
4. Mở rộng shopping cues bằng các mẫu có oracle và negative pairs, như “cần”, “cho mình xem”, “có…không”. Câu “không mua”, “mình vừa mua” không tự trở thành lệnh đặt hàng. Search không thực hiện giao dịch.
5. Đo coverage từ vựng đã tạo từ catalog: bao nhiêu category/tên nhóm được nhận, bao nhiêu cụm bị cap/loại. Giữ public-port gates và vòng đời snapshot có phiên bản; không thêm toàn bộ mô tả/import metadata làm từ vựng.

### Ưu tiên2: thử term hints có đối chứng nếu lỗi audio tập trung vào tên hàng

faster-whisper1.2.1 có `hotwords` và `initial_prompt`. Trong [mã nguồn chính thức](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/transcribe.py), hotwords được đưa vào token prompt, có giới hạn độ dài và không tác dụng khi dùng `prefix`. Đây không phải bảo đảm âm học, từ điển bắt buộc hay xác suất sản phẩm đã hiệu chuẩn. Prompt danh mục dài và prompt ngắn đã làm một số nhóm audio yếu hơn trong [SEARCH_QUALITY_REPORT](SEARCH_QUALITY_REPORT.md); không chạy lại các cấu hình đó rồi chọn theo test.

Một thử nghiệm mới chỉ hợp lý khi có audio mua sắm development và lỗi tên hàng cụ thể: hint tối đa một tập nhỏ từ server, dựa trên category người dùng đã chọn hoặc snapshot public; không lấy reference của từng case, không lấy catalog draft, không nhận hotwords tùy ý từ client. Freeze cách chọn/budget trước khi giải mã. So với Pho không hint trên cùng audio; chấm product/slot success và hallucination ngoài miền, không chỉ WER. Nếu làm mất “không”, thay số tiền/màu hoặc tăng false product thì loại.

Hiện port `SpeechRecognizer.transcribe(content,mime,filename)` và worker nhận raw audio, chưa có contract trusted-context. Không nhét tùy ý vào filename/header hoặc cho worker đọc SQL. Nếu triển khai sau, context phải được tạo ở application service qua domain port, giới hạn dữ liệu tại API/worker và có phiên bản; giữ single-job/local-only gate.

### Ưu tiên3: alternatives có bằng chứng từ decoder

[CTranslate2 Whisper.generate](https://opennmt.net/CTranslate2/python/ctranslate2.models.Whisper.html) hỗ trợ số hypothesis trả về và score. `WhisperModel.transcribe` hiện trả một transcript qua API đang dùng; không thể coi `beam_size=3` là đã có3 câu thay thế trong response. Việc dùng n-best cần đường decode/segment riêng và contract có kiểm thử, không chỉ đổi một flag.

Có thể nghiên cứu n-best trên cùng Pho để đưa tối đa2–3 phương án nghe được. Tuy nhiên, relevance của catalog chỉ được dùng đề xuất phương án có xác nhận, không âm thầm chọn câu “có hàng” hơn. Nếu các phương án khác nhau về giá, màu, phủ định hoặc mã đơn thì đánh dấu cần kiểm tra; vẫn hiển thị câu ASR gốc. Chi phí CPU/độ trễ phải đo; không mặc định n-best miễn phí hoặc chính xác hơn.

### Ưu tiên4: chất lượng đầu vào và VAD có kiểm soát

VAD xác định vùng có tiếng nói, không sửa âm gần giống. faster-whisper dùng Silero; [mã VAD1.2.1](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/vad.py) có ngưỡng, thời gian im lặng và padding. [Silero chính thức](https://github.com/snakers4/silero-vad) cung cấp mô hình phát hiện tiếng nói, không phải bộ hiểu tên sản phẩm.

Worker hiện VAD=False. Với câu ngắn≤15s, bật VAD tùy tiện có thể làm mất âm nhẹ ở đầu/cuối, nhất là từ phủ định, đơn vị giá hay phụ âm cuối. Chỉ thử sau khi kiểm kê artifact VAD đã cài, không tải model mới. Dùng một config development có padding rõ ràng, kiểm cả câu rất ngắn, im lặng đầu/cuối, âm yếu/nhiễu. Nếu thấy cắt lời thì giữ False. Không dùng chuẩn hóa biên độ hoặc khử nhiễu mạnh nếu chưa đo; tăng gain không khôi phục thông tin đã clipping.

Nên thông báo ngắn khi clip quá nhỏ/không có tiếng, gần chạm giới hạn hoặc cần ghi lại; không thêm hộp kỹ thuật cho người mua. Chỉ số RMS/clipping đo tín hiệu, không phải confidence của tên hàng. `avg_logprob` hiện cũng chưa được hiệu chuẩn thành xác suất câu đúng; không hiển thị thành “độ chính xác90%”.

### LLM và API miễn phí

Dự án chưa có local LLM được duyệt/cài. OpenCLIP hiện có dùng cho ảnh/text embedding, không phải bộ nghe/sửa câu tiếng Việt. Một LLM mới sẽ thêm weights, RAM/CPU và latency, vẫn cần kiểm slot và có thể đoán câu hợp catalog nhưng sai lời nói. Vì chưa có bằng chứng parser/hints không đạt, chưa đề xuất thêm model hoặc fine-tuning. Dịch vụ cloud free-tier không thỏa ràng buộc hiện tại `LOCAL_ONLY=true`; không tự chuyển audio ra ngoài máy hoặc dựa vào quota miễn phí để cam kết vận hành.

## 4. Guardrails và phép thử cần khóa

- Bảo toàn nguyên câu; correction/alternative có provenance riêng và được người dùng chọn. Không tự tìm bằng một câu đã thay âm thầm.
- Không sửa giá, số lượng, màu, chất liệu, giới tính, size, phủ định, order ID bằng fuzzy catalog matching. Các giá trị mơ hồ phải xác nhận; UI-selected filters tiếp tục ưu tiên.
- Không dùng sản phẩm bị cấm/nháp/unverified làm hint hoặc oracle relevant; không gỡ hard filters để tăng hit rate.
- Giữ các ca negative: câu không mua sắm, hai loại hàng, hàng hợp lệ nhưng catalog thiếu, phủ định màu, giá tương cận50/500/550 nghìn, giọng nhỏ, ngập ngừng, noise, brand/model có số và order intent. Không ghi âm ngoài thao tác rõ ràng của người dùng.
- Tách development / validation khóa trước; không sửa config theo transcript validation. Lưu hash audio, catalog snapshot, config, qrels và kết quả raw ASR → parsed slots → candidate IDs → top products.
- Báo first-pass, assisted, latency và lỗi điều kiện cứng cho từng nhóm. Nếu chỉ có100 case text thì ghi đúng “text retrieval”, chưa chứng nhận70% spoken shopping. Cần audio mua sắm thật có quyền dùng; không tải corpus mới hoặc lấy giọng người dùng khi chưa được cho phép.

## Kết luận triển khai

Đường ít tốn tài nguyên nhất hiện tại là **giữ Pho đã đo, chấm100 oracle text để sửa lỗi hiểu câu/xếp hạng trước**, rồi chạy audio mua sắm qua cùng pipeline. Chỉ thử hint/n-best/VAD khi phân tích lỗi cho thấy chúng giải quyết nút thắt có thật. Không thay metric70% bằng `1-WER`, không lấy gợi ý gần âm hoặc một vài clip đọc chung làm kết quả nghiệm thu mục tiêu người mua.
