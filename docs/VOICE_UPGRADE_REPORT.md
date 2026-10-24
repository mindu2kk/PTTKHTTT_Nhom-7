# Nâng cấp nhận giọng tiếng Việt — 2026-10-23

Đã chọn **PhoWhisper-base int8 CPU**, profile `phowhisper-base`, chạy cục bộ với `without_timestamps=true`. `.env` máy hiện tại đã đổi đúng một lựa chọn ASR; weights base cũ vẫn giữ để rollback. Không API trả phí/cloud inference. Kế hoạch: [VOICE_UPGRADE_PLAN](VOICE_UPGRADE_PLAN.md).

## Ba agent và phần tích hợp

| Phần | Việc đã làm |
|---|---|
| ASR engine | Sửa flush resampler EOF; model profile, kiểm toàn vẹn trước load; converter offline và cấu hình timestamp đúng với inference chính thức |
| Ngữ cảnh sản phẩm | Từ vựng lấy qua public catalog port, kiểm verified/nguồn/quyền ảnh; tối đa256 cụm và3 gợi ý. Cần anchor/ngữ cảnh mua sắm, người dùng chọn xác nhận |
| Kiểm thử độc lập | Đóng băng audio/hash/split; baseline/fresh/candidate chạy tuần tự, WER/CER và paired bootstrap theo speaker; giữ cả clip hồi quy |
| Tích hợp | Download có đồng ý, checksum/license, chuyển int8, API nhận đúng revision, composition qua domain ports, rollout local và regression |

Câu gốc vẫn giữ nguyên. Không tự sửa số tiền, màu, mã đơn, thuộc tính hoặc biến các tên đều hợp lệ thành nhau. Từ vựng không nhận từ client/import/nháp: `SpeechService` chỉ đọc `CatalogRepository.list_products` sau khi ASR thành công. Nếu catalog lỗi, giữ transcript và báo gợi ý tạm không sẵn sàng. Generic suggestion có giới hạn, không phải hiểu ngữ cảnh tiếng Việt tổng quát; không tính các gợi ý vào WER.

## Thay đổi đã làm chất lượng nghe tốt hơn

PhoWhisper-base cùng cỡ74M với base cũ, được chuyên biệt cho tiếng Việt. Chỉ đổi weights trong lượt đầu giúp một phần nhưng vẫn có ca hồi quy. Sau đó phát hiện cấu hình HF chính thức `return_timestamps=false`, còn faster-whisper mặc định `without_timestamps=false`. Pho profile đã thêm token không timestamp bằng `without_timestamps=true`; base rollback giữ False. Các tham số khác giữ beam3/best_of3/temperature0/previous_text=False/VAD=False/max160/repetition1.1/ngram3.

Nguồn đối chiếu: [PhoWhisper/VinAI](https://github.com/VinAIResearch/PhoWhisper), [model/config gốc](https://huggingface.co/vinai/PhoWhisper-base/tree/7ebdb9e88f5cc5271fb88f4d642c82ff9388650e), [Transformers4.31 Whisper.generate](https://github.com/huggingface/transformers/blob/v4.31.0/src/transformers/models/whisper/modeling_whisper.py), [faster-whisper1.2.1](https://github.com/SYSTRAN/faster-whisper/blob/v1.2.1/faster_whisper/transcribe.py). Không dùng WER do tác giả công bố làm kết quả của ứng dụng.

## Đo đối chứng thực tế

WER là tỷ lệ lỗi từ, không đổi thành “độ chính xác” bằng phép trừ100%. Chấm NFC/lowercase, punctuation thành khoảng trắng, collapse; giữ dấu và chữ số. Không sửa transcript bằng từ vựng sản phẩm trước chấm.

| Bộ audio | Base WER | Pho text-only WER | Phạm vi |
|---|---:|---:|---|
| **V2:29 câu mới,279 từ,19 speaker ID** | **36,56%** | **7,53%** | Freeze trước ablation; khóa config trước mọi ASR V2; chưa xem utterance output trước quyết định |
| V1:29 clip, kiểm lại |43,78%|22,75%| Đã mở số liệu trước ablation; repeated validation |
| VIVOS20 development cũ |23,92%|5,26%| Dữ liệu đã dùng kiểm cấu hình, không phải test độc lập |
| ViMD9 development cũ |61,97%|37,61%| Regional smoke nhỏ, còn lỗi nhiều |

**V2:** CER17,55%→3,80%; số câu hoàn toàn đúng2→16/29;26 câu ít lỗi hơn,0 nhiều lỗi hơn,3 không đổi. Delta WER=-0,2903; bootstrap95% theo cụm speaker [-0,3673;-0,2409], seed20261023/2000 resamples. Không HTTP lỗi ở hai model. [Đối chiếu V2](evidence/voice-upgrade/evaluation-v2-paired.json), [khóa cấu hình](evidence/voice-upgrade/evaluation-v2-configuration-lock.json), [manifest](evidence/voice-upgrade/evaluation-v2-manifest.json).

**V1 repeated:** VIVOS9 WER25,32%→10,13%, ViMD20 WER45,94%→24,22%; CER cả hai corpus cũng tốt hơn.26 clip ít lỗi,1 nhiều lỗi,2 không đổi. Clip ViMD70_0274 vẫn hồi quy25→30 word errors/51 từ; không xóa ca này khỏi báo cáo. [Đối chiếu V1](evidence/voice-upgrade/evaluation-repeated-v1-paired.json).

Lượt đầu Pho chưa sửa timestamp và ba thử decoder cũ đều được giữ riêng; không ghi đè để che kết quả yếu. [Review độc lập](evidence/voice-upgrade/evaluation-final-review.json) lưu hash các nguồn và diễn biến lựa chọn. [Model selection](evidence/voice-upgrade/model-selection.json) ghi gate đã dùng khi đổi `.env`.

### Giới hạn của phép đo

- V2 độc lập theo **utterance**, có trùng speaker đã gặp và chỉ có VIVOS. Không gọi là speaker-independent, không đại diện giọng mua sắm/noise/mixed-English.
- V1 ban đầu có29 speaker ID mới so development, nhưng đã mở kết quả trước sửa timestamp. Lần cuối chỉ là kiểm lặp, không còn blind. Chênh baseline gốc với fresh-fixed là1/756 word error do pipeline/điều kiện chạy; so final với fresh-fixed cùng decode để tách rõ.
- VIVOS/ViMD là giọng đọc/phát thanh; không phải audio TC2 người dùng hoặc micro vật lý. VIVOS CC-BY-NC-SA4.0 (Luong & Vu), ViMD CC-BY-NC-ND4.0 (Nguyen Dinh et al.), chỉ kiểm học thuật private, không phân phối audio/reference/hypothesis gốc trong evidence public.
- Model vẫn có lỗi; không tuyên bố nhận đúng mọi âm gần hoặc hết lỗi tìm kiếm. Bước kiểm tra/sửa câu và gợi ý có xác nhận vẫn cần.

## Tài nguyên, nguồn và bảo toàn dữ liệu

Download được user đồng ý riêng: **294.056.285bytes**, official revision `7ebdb9e88f5cc5271fb88f4d642c82ff9388650e`, BSD-3-Clause. CheckpointSHA256 `910b9e8875497078efa83dc506ea7ee378e4e759a206ceecbf23e088aec9b9f8`. [Acquisition](evidence/voice-upgrade/model-acquisition.json).

Chuyển CT2 int8 bằng Torch2.9.1+cpu/Transformers4.57.6/CT2 4.8.3: thư mục runtime7 tệp khoảng**79,67MB**, kèm LICENSE/README. Converter ép `weights_only`, `local_files_only`, không remote code; manifest nguồn/kích thước/hash được kiểm lúc load model. [Conversion](evidence/voice-upgrade/model-conversion.json). Transformers/Hub/tokenizers cài trong thư mục conversion tạm, không thêm vào production requirements.

Production giữ một ASR,2 CPU threads, worker gate1; CLIP được load lazy riêng như trước. V2 ASR-only RSS sau request lớn nhất được báo: base283,94MiB/Pho270,41MiB; đây không phải sampled process peak hoặc RAM khi CLIP cùng load. V2 wall p50≈1309→1601ms, p95≈2370→2208ms: **không nhanh hơn ở mọi trường hợp**, không cam kết SLA. Các lượt khác có host load khác; không ghép timing để quảng bá tăng tốc. Không tăng model sang small/large, không tải dataset mới.

Container đánh giá19091 đã dừng/xóa sau đo; data/models mount chỉ đọc. Không đổi schema, reset DB chính, seed lại giá/đơn hoặc reindex catalog. `.env.example` vẫn dùng base cho máy mới chưa đồng ý tải model khác.

## Kiểm thử bản đã tích hợp

| Gate | Kết quả / evidence |
|---|---|
| API unit offline |157 passed/1,04s — [log](evidence/voice-upgrade/api-unit.txt), [JUnit](evidence/voice-upgrade/api-unit.xml) |
| API integration, upload/ownership negatives |187 passed/54,39s, DB `_test` riêng — [log](evidence/voice-upgrade/api-integration.txt), [JUnit](evidence/voice-upgrade/api-integration.xml) |
| Worker unit thực PyAV/profile/hash |20 passed/0,299s — [log](evidence/voice-upgrade/inference-unit.txt), [JUnit](evidence/voice-upgrade/inference-unit.xml) |
| Scorer/paired/protocol guards |20 passed/0,86s — [log](evidence/voice-upgrade/evaluation-unit.txt), [JUnit](evidence/voice-upgrade/evaluation-unit.xml) |
| Ruff/format/mypy |Đạt,40 app source files;129 files đúng format — `evidence/voice-upgrade/{ruff,format,mypy}.txt` |
| Docker local |API/inference build và4 services healthy — [services](evidence/voice-upgrade/services.txt), `artifacts/voice-upgrade-delivery-build.txt` |
| Chrome end-to-end |Đạt text5viewport, image/CLIP, paste event, permission/cleanup và actual MediaRecorder→PhoWhisper; [log](evidence/voice-upgrade/browser.txt), [JSON](evidence/voice-upgrade/browser/browser.json) |

Chrome dùng fake microphone phát clip VIVOS thật, không phải micro vật lý. Clipboard harness phát ClipboardEvent với bytes ảnh, không phải OS clipboard automation. Test giả lập permission/provenance/response bị lỗi tách khỏi đo chất lượng ASR.

## Chạy lại và rollback

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/unit_tests -q
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q
.\.venv\Scripts\python.exe -m pytest benchmarks/scripts/voice_eval_test.py benchmarks/scripts/voice_eval_v2_test.py -q
# .env hiện ASR_MODEL_PROFILE=phowhisper-base; chỉ chạy khi đã có model được đồng ý:
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait api inference
$env:INLINE_SEARCH_EVIDENCE='docs/evidence/voice-upgrade/browser-new-run'
.\.venv\Scripts\python.exe benchmarks/scripts/inline_search_browser.py
```

Tái tạo weights: chỉ sau đồng ý, `scripts/acquire_phowhisper.py --consented`; convert snapshot local bằng `apps/inference/convert_phowhisper.py source output-mới` trong môi trường có conversion dependencies. Không tự tải khi startup/search. Không ghi đè output/evidence đã có. Lệnh frozen evaluation tại [V1 protocol](evidence/voice-upgrade/evaluation-protocol.md) và [V2 protocol](evidence/voice-upgrade/evaluation-v2-protocol.md).

Rollback: đổi đúng dòng `.env` thành `ASR_MODEL_PROFILE=whisper-base`, rồi `docker compose --env-file .env -f infra/docker-compose.yml up -d --no-deps --wait inference`. Không đụng DB/models cũ.

## Tệp chính

`apps/inference/{main,audio_decode,asr_profiles,convert_phowhisper}.py`, Dockerfile/tests; API SpeechService/speech_context/dependencies/media adapter và unit tests; compose/profile example; acquisition/benchmark/metric/V2/unit runners; plan/report/current progress/runbook options. Model và audio private không đưa vào kho công khai. Không sửa giao diện thêm hộp hoặc đổi luồng thu âm tại chỗ.
