# Validation V2 sau kiểm tra tương thích PhoWhisper

V1 đã được mở trước khi kiểm tra riêng `without_timestamps=True`; vì vậy, các lượt V1 với tùy chọn mới là **validation lặp**, không phải kiểm định blind mới. V2 được đóng băng trước lần ablation development duy nhất `pho-text-int8` và trước khi quyết định cấu hình. Không thay manifest, runner hoặc kết quả V1.

## Tập mới và nguồn

`evaluation-v2-manifest.json` ghi SHA256 của manifest riêng, nguồn archive và từng audio. Manifest riêng SHA256 **a2784e85197e34d4185d7b8d424147e9ed2d04774f3e9891753ada5ac37b94cc**. Chỉ dùng hai parquet cục bộ có từ trước; không tải thêm hoặc biến đổi WAV.

Lọc bỏ mọi SHA audio và câu tham chiếu chuẩn hóa đã có trong58 clip V1. Điều kiện giữ nguyên1–12 giây, tối đa2MiB, byte WAV nguyên bản. Chọn theo thứ tự parquet cố định, ưu tiên câu đầu mỗi speaker ID rồi điền câu còn lại theo thứ tự nguồn. Mục tiêu15 VIVOS+14 ViMD; phần thiếu được bù từ corpus còn lại, không xem giả thuyết ASR để chọn.

**Kết quả:**29 utterance VIVOS mới,19 speaker ID. Không còn ViMD đủ điều kiện sau khi loại V1, nên toàn bộ quota được bù bằng VIVOS. Không gọi V2 là tập cân hai corpus, kiểm định3miền hay speaker-independent. Speaker có thể trùng development/V1; chỉ độc lập theo utterance và câu tham chiếu, không chứng minh độc lập với dữ liệu huấn luyện upstream. Quyền VIVOS CC-BY-NC-SA-4.0, Luong & Vu, kiểm học thuật cục bộ; audio và câu nguồn không đưa vào bằng chứng công khai.

## Khóa cấu hình trước khi nghe V2

`voice_eval_v2_run.py lock` chỉ chấp nhận bằng chứng có `split=development`, ghi SHA bằng chứng, thời điểm, hash V2 và cấu hình baseline/candidate. Từ chối ghi đè quyết định. `run` từ chối suy luận khi chưa có lock; kiểm health worker thật khớp profile và `asr_without_timestamps` đã chọn. Baseline là Whisper base, without_timestamps=false; candidate là PhoWhisper base với giá trị được coordinator quyết định từ cấu hình nhà phát hành và ablation development.

Runner dùng chung khóa inference benchmark với V1, xử lý tuần tự qua worker local; không retry/ẩn429. Một warmup development cũ được ghi riêng, không thuộc29 mẫu mới. Các số WER/CER dùng nguyên `voice_eval_metrics.py` của V1; không thay số, tên sản phẩm hoặc dùng gợi ý ngữ cảnh để chấm âm học. Lỗi HTTP tính giả thuyết rỗng. File công khai không chứa câu tham chiếu/giả thuyết; chẩn đoán riêng lưu trong `data/private/voice-upgrade/v2/`.

Chạy chỉ in trạng thái/đường dẫn, không in score. Sau cả hai lượt cùng manifest/cấu hình khóa, dùng runner V1 `compare` để chấm cặp và bootstrap theo speaker ID. Bootstrap trên V2 không biến tập có trùng speaker với development thành speaker-independent.

## Lệnh

```powershell
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_v2_corpus.py verify
.\.venv\Scripts\python.exe -m pytest benchmarks/scripts/voice_eval_v2_test.py -q
# Chỉ sau coordinator chọn true từ development:
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_v2_run.py lock --candidate-without-timestamps true --development-evidence docs/evidence/voice-upgrade/evaluation-pho-text-int8-development.json
# Worker temporary19091 đúng profile baseline; cần coordinator cấp CPU:
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_v2_run.py run --label base-fixed --role baseline --endpoint http://127.0.0.1:19091/transcribe
# Coordinator đổi temporary worker sang profile candidate đã khóa, rồi cấp CPU:
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_v2_run.py run --label pho-text-int8 --role candidate --endpoint http://127.0.0.1:19091/transcribe
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_run.py compare docs/evidence/voice-upgrade/evaluation-v2-base-fixed.json docs/evidence/voice-upgrade/evaluation-v2-pho-text-int8.json --output docs/evidence/voice-upgrade/evaluation-v2-paired.json
```

Kiểm đơn vị V2:6 ca selector/quota0/thứ tự/khóa cấu hình. Cộng với14 ca scorer ban đầu là20 ca công cụ benchmark; không cộng chúng vào số unit test API/FE hay xem là chứng nhận ASR.

Giới hạn giữ nguyên: giọng đọc, chưa có shopping oracle/micro vật lý/TC2. RSS worker báo sau request không phải process peak; thời gian quan sát một lượt không đủ kết luận tăng tốc hay SLA. Bất kỳ sửa cấu hình sau khi mở V2 sẽ khiến lượt sau trở thành validation lặp trên tập đã xem.

## Kết quả sau khi khóa cấu hình

Coordinator chọn PhoWhisper-base `without_timestamps=True` dựa trên cấu hình nhà phát hành và một ablation development. Các tham số beam3/best3/temp0/previous_text=false/VAD=false/max_tokens160/repetition1.1/ngram3 giữ nguyên, có sidecar bất biến `evaluation-v2-decoder-lock.json`. Configuration lock tạo trước mọi suy luận V2. Sau baseline V2 chỉ đọc log trạng thái; chỉ mở số đo khi candidate V2 cũng đã kết thúc.

| V2:29 utterance mới,279 từ | Whisper base | PhoWhisper base text-only |
|---|---:|---:|
| WER |36.5591%|7.5269%|
| CER kể khoảng trắng |17.5527%|3.7975%|
| Câu khớp hoàn toàn |2/29|16/29|
| HTTP lỗi |0|0|
| RSS worker lớn nhất được báo |283.94MiB|270.41MiB|
| Wall p50 |1308.59ms|1600.69ms|
| Wall p95 |2369.59ms|2207.61ms|

WER giảm tương đối79.4118%;26 clip ít lỗi hơn,0 clip nhiều lỗi hơn,3 không đổi. Delta WER=-0.290323; bootstrap theo19 speaker ID,2.000 lượt, CI95%[-0.367347,-0.240896]. Đây là cải thiện trên dữ liệu đọc được đo, không diễn giải WER thành tỷ lệ câu/ý định mua sắm đúng. Median wall của candidate cao hơn; không tuyên bố nhanh hơn ở mọi yêu cầu. Initial warmup dùng lại clip development, lần đầu có tải model: baseline4330.60ms/model_load2949.54ms, candidate4454.13ms/model_load3019.75ms; OS cache không bị xóa.

Đối chứng V1 đã mở, chạy lại với cấu hình đã khóa: WER43.7831%→22.7513%, CER24.9146%→14.7561%; VIVOS9 WER25.3165%→10.1266%, ViMD20 WER45.9380%→24.2245%. Cả hai corpus giảm WER/CER;26 clip ít lỗi,1 clip nhiều lỗi,2 không đổi. Clip ViMD70_0274 tăng25→30 lỗi trên51 từ, cho thấy vẫn có hồi quy. Không nhận V1 lần này là blind mới.

Development VIVOS20 cũ: WER23.9234%→5.2632%, CER12%→2.5143%. ViMD9 development: WER61.9658%→37.6068%, CER37.1032%→22.6190%. Đây là tập đã dùng chọn cấu hình, không phải gate độc lập. Bằng chứng tổng hợp có hash nguồn tại `evaluation-final-review.json`, tạo bằng `voice_eval_review.py`; profile production do coordinator xem xét và triển khai riêng.
