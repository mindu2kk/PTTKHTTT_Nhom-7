# Giao thức đánh giá ASR độc lập — 2026-10-23

Đã đóng băng manifest trước bất kỳ lần suy luận mới nào của đợt này. Nguồn chỉ là hai parquet đã có trên máy; không tải dataset hoặc trọng số. Manifest công khai `evaluation-manifest.json` có SHA256 của manifest riêng, từng audio và hai archive. Không đưa audio, bản chép lời nguồn vào bằng chứng công khai.

## Tách dữ liệu

- **Development:** 20 clip VIVOS và 9 clip ViMD đã từng dùng; 29 clip, 18 ID người nói. Có thể dùng để chẩn đoán/điều chỉnh, không gọi là kiểm định độc lập.
- **Heldout:** 29 clip từ 29 ID người nói chưa xuất hiện trong development, gồm 9 VIVOS và 20 ViMD. Chọn câu đầu tiên đủ 1–12 giây, WAV gốc không sửa và dưới 2 MB, theo thứ tự parquet cố định; không chọn bằng kết quả model. Không trùng người nói giữa hai nhóm, có kiểm bằng mã.
- Ban đầu dự kiến 24 người ViMD nhưng archive cục bộ chỉ có 20 người mới đủ điều kiện; đóng băng 20, không bỏ clip dựa theo độ khó. 19 clip ViMD South, 1 Central; không có North mới. VIVOS không có nhãn miền.
- Đây là **heldout đối với việc tuning của dự án**, không chứng minh các model upstream chưa từng học nguồn này.
- VIVOS: Hieu-Thi Luong và Hai-Quan Vu, CC-BY-NC-SA-4.0. ViMD: Nguyen Dinh và cộng sự, CC-BY-NC-ND-4.0. Chỉ kiểm học thuật cục bộ, byte âm thanh giữ nguyên và không tái phân phối. Nguồn/giấy phép theo hồ sơ rights đã lưu của dự án.

## Metric

Primary acoustic WER: Unicode NFC, lowercase, mọi ký tự không phải chữ/số/khoảng trắng thành một khoảng trắng, rồi collapse whitespace. Giữ dấu tiếng Việt; không thay từ đồng âm, tên sản phẩm, chữ số hay cách nói tiền. WER là tổng lỗi Levenshtein chia tổng từ tham chiếu, không lấy trung bình WER từng clip; có thể lớn hơn 1. CER dùng cùng chuỗi chuẩn hóa, kể cả khoảng trắng giữa từ. Request lỗi được tính giả thuyết rỗng, không bỏ khỏi mẫu số.

Chấm lại 20 giả thuyết VIVOS lịch sử bằng normalizer này vẫn WER **0.23923444976076555** (`evaluation-historical-normalizer.json`); normalizer cũ không phải nguyên nhân chính của số 23,9% đã báo. Quy tắc mới sửa nguy cơ nối từ ở dấu câu và nhiều khoảng trắng trong CER.

Không có nhãn ý định mua sắm/giá/tên sản phẩm từ giọng người thật nên **không báo intent accuracy hoặc number-normalized WER như cải thiện âm học**. Bảy giọng TTS cùng một câu không được đưa vào primary. Không có tệp TC2 của người dùng nên không đóng TC2.

So sánh phải cùng thứ tự ID/audio SHA, manifest, split và normalizer. Báo riêng overall, mỗi corpus, regional smoke khi có nhãn, 5 clip WER xấu nhất; số clip ít lỗi/nhiều lỗi hơn và exact-match tăng/giảm. Bootstrap cặp theo cụm người nói 2.000 lượt, seed 20261023; CI mô tả bất định của mẫu nhỏ, không chứng minh tác dụng trên mua sắm thực tế.

Manifest đóng băng ban đầu chưa sao chép nhãn vùng của 9 clip development. `voice_eval_regional.py` nối riêng nhãn theo ID từ `data/private/vimd/regional-selection.json` có từ trước, lưu SHA của metadata đó trong bằng chứng; không đổi manifest hoặc các nhóm primary. Báo riêng 3 clip North/3 Central/3 South đã từng dùng, chỉ là developmental smoke. Cùng script có thể đối chiếu baseline/candidate; không chạy inference thêm.

## Runtime và tránh tranh CPU

Chỉ chạy khi coordinator cấp lượt. Một request tại một thời điểm qua worker HTTP loopback `/transcribe`; vẫn qua semaphore của worker. Runner có khóa riêng ngăn hai lượt runner cùng chạy; không retry hay che 429. Không chạy integration/CLIP/ASR benchmark khác đồng thời.

Request đầu tiên dùng một clip development làm warmup, báo riêng model-load/wall/RSS, không gọi là cold nếu process/OS cache chưa được làm lạnh. Mỗi split sau đó ghi wall và inference time; p50/p95 của các request thành công, tổng lỗi báo riêng. RSS là RSS worker báo sau mỗi request, giá trị lớn nhất **không phải process peak được sampling**. Không diễn giải thời gian raw worker thành SLA của FE/BFF/API.

Model/config phải được coordinator ghi nhận khi tái tạo worker. Đối chiếu acoustic upgrade dùng decoder cố định; không tune vào heldout. Nếu xem heldout rồi sửa ứng viên, lần đo tiếp theo chỉ là validation lặp lại, không còn là kiểm định mới.

## Lệnh tái kiểm

```powershell
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_corpus.py verify
.\.venv\Scripts\python.exe -m pytest benchmarks/scripts/voice_eval_test.py -q
# Sau khi được cấp lượt CPU, trước khi đổi baseline worker:
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_run.py run --label base-int8 --split development
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_run.py run --label base-int8 --split heldout
# Sau khi coordinator đổi candidate nhưng giữ decoder/config công bằng:
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_run.py run --label candidate --split development
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_run.py run --label candidate --split heldout
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_run.py compare docs/evidence/voice-upgrade/evaluation-base-int8-heldout.json docs/evidence/voice-upgrade/evaluation-candidate-heldout.json --output docs/evidence/voice-upgrade/evaluation-paired-heldout.json
.\.venv\Scripts\python.exe benchmarks/scripts/voice_eval_regional.py docs/evidence/voice-upgrade/evaluation-base-int8-development.json --candidate docs/evidence/voice-upgrade/evaluation-candidate-development.json --output docs/evidence/voice-upgrade/evaluation-paired-regional-development.json
```

Runner từ chối ghi đè bằng chứng. Transcript chẩn đoán chỉ lưu dưới `data/private/voice-upgrade/`. Kết quả nghe phải được báo cùng giới hạn: giọng đọc/phát thanh, một clip mỗi heldout speaker, lệch miền, không micro vật lý, không đủ chứng minh từ gần âm mua sắm đã hết lỗi.

## Baseline đã đo

Worker gốc `faster-whisper1.2.1`, Whisper base int8; decoder beam3, best_of3, temperature0, previous_text=false, VAD=false, max_new_tokens160, repetition_penalty1.1, no_repeat_ngram_size3. SHA256 mã nguồn worker và decoder AST trong `evaluation-base-runtime.json`. Lệnh lấy runtime đầu thiếu `--env-file .env` bị lỗi nội suy Compose; đã thêm cờ và chạy lại, log lỗi giữ riêng, không đổi cấu hình hay lộ credential.

| Nhóm | Clip / ID người nói | WER | CER | HTTP lỗi |
|---|---:|---:|---:|---:|
| Development VIVOS | 20 / 10 | 0.2392344498 | 0.1200000000 | 0 |
| Development ViMD | 9 / 8 | 0.6196581197 | 0.3710317460 | 0 |
| Heldout VIVOS | 9 / 9 | 0.2531645570 | 0.1161473088 | 0 |
| Heldout ViMD | 20 / 20 | 0.4579025111 | 0.2690160502 | 0 |
| Heldout gộp theo từ | 29 / 29 | 0.4365079365 | 0.2522522523 | 0 |

Heldout có 756 từ tham chiếu, trong đó 677 từ ViMD; số gộp chịu trọng số ViMD. Không dùng số23,9% development VIVOS để đối chiếu với số heldout gộp khác tập. Tất cả58 clip và2 warmup trả200. Heldout wall p50=3665.059ms, p95=6347.555ms; development p50=2320.954ms, p95=4271.952ms. Không suy ra SLA từ lượt tuần tự này.

RSS tối đa được worker báo trong heldout1245.85MiB; health cho thấy **CLIP và ASR đã cùng load từ trước**. Model_load_ms của initial request=0. Candidate worker mới chỉ tải ASR sẽ không có nền RAM tương đương; không tuyên bố tiết kiệm RAM của riêng model bằng hai trạng thái khác nhau. Health/giới hạn trong `evaluation-base-int8-health.json`.

Supplemental development theo miền: North3 clip WER0.50704, Central3 clip0.62500, South3 clip0.71084 (`evaluation-base-regional-development.json`). Heldout chỉ có South19 clip và Central1 clip; không dùng để chứng nhận chất lượng3miền.
