# Số đo thật và giới hạn

Máy: Intel Core i3-1315U, 8 logical processors, RAM15.73GiB, Windows11 Pro; DB/worker trong Docker Linux, worker CPU threads2, không GPU. `evidence/hardware.json`. Các lần đo khác nhau có thể chịu contention build/ASR; không gọi số đo một lần là SLA.

## 3.000 sản phẩm, 204 câu tiếng Việt

2950 clone fixture +50 public gốc, tổng3005 stored; DB `_test` riêng, không reset main, dọn exact run IDs trong finally. 34 leaf×6 dạng câu: có/không dấu, lời mua, giá số/giá chữ và màu. Đáp án category/color/price viết theo cấu trúc fixture, **không phải human semantic judgments**. Từng lượt dùng API native qua HTTPX ASGITransport + PostgreSQL thật: gồm validation/serialize/SQL, không gồm TCP/uvicorn network overhead. Warm10 trước mỗi nhóm; 204 request/nhóm, concurrency1/5/10. Qrels: `benchmarks/qrels/synthetic-204.json`.

| Đồng thời | Service p50 ms | Service p95 ms | ASGI HTTP p95 ms |
|---:|---:|---:|---:|
| 1 | 97.794 | 152.08 | 169.224 |
| 5 | 119.14 | 210.235 | 247.741 |
| 10 | 333.655 | 569.867 | 808.853 |

Precision@10=1, NDCG@10=1, Recall@10≈0.11349, hard-filter leaks=0 theo các oracle cấu trúc. Recall thấp vì mỗi leaf có khoảng86–100 relevant items còn K=10; không diễn giải như chất lượng nhận diện sản phẩm thực. Lượt đầu phát hiện búp bê→be và tối đa→da; đã sửa/parser test; trước sửa lưu `scale-before-parser-fix.json`. EXPLAIN thấy estimated1/actual3000, đã ANALYZE sau bulk import thay vì thêm ANN/GIN thiếu bằng chứng. Before/after và plan JSON giữ trong evidence; không khẳng định ANALYZE luôn nhanh hơn.

Grid: 100 request/nhóm, 10 trang luân phiên:

| Đồng thời | ASGI HTTP p95 ms |
|---:|---:|
| 1 | 170.553 |
| 5 | 219.614 |
| 10 | 737.932 |

Không có hybrid semantic≤900ms claim. Số đo HTTP qua TCP trên fixture55 gốc nằm riêng `text-benchmark.json`/`catalog-benchmark.json`, không gộp với 3k.

Lượt tối ưu mới đạt text service≤300ms ở c1/c5, chưa đạt c10; grid ASGI≤400ms ở c1/c5. Đã chuyển source bị cấm thành tập ID hashable, nối offer→variant bằng FK thay vì lặp điều kiện product, UNION cho cây giao nhau. Composite FK vẫn chặn offer sai product. EXPLAIN grid giảm khoảng51k xuống478 shared buffer hits, actual startup≈46ms; trước sửa giữ tại `scale-plan-before-rights-optimization.json`. Không thay đổi quyền/giá/stock để cải thiện số đo.

### HTTP thật trên Docker — số đo triển khai cục bộ

`scripts/benchmark-http.ps1` mở API riêng cổng8002 dùng DB `hoodoomart_test`, giữ cùng corpus 3k/204 queries; đo Windows HTTPX→TCP loopback→Docker API Python3.12→PostgreSQL. Không chạy build/ASR trong lượt cuối; API benchmark được stop/remove sau đo. `scale-3000-http.json`; lượt bị contention build giữ riêng `scale-http-during-build.json`, không gộp chọn số đẹp.

| Đồng thời | Search service p95 ms | Search TCP p95 ms | Grid TCP p95 ms |
|---:|---:|---:|---:|
| 1 | 109.468 | 133.021 | 157.563 |
| 5 | 141.085 | 218.071 | 280.441 |
| 10 | 381.111 | 577.541 | 435.314 |

Target là mục tiêu đo, không SLA; mức10 đồng thời còn giới hạn. Qrels HTTP riêng `synthetic-204-http.json`; IDs scale đã được dọn đúng run, không reset dữ liệu main.

## Ảnh thật bằng OpenCLIP

M4 offline50 gallery:39.824s, model load20.022s, RSS snapshot976.59MiB. API query đầu2800.551ms trong worker đã dùng để tạo chỉ mục; cache-hit repeat p95129.739ms **không phải uncached inference**. Curated navy illustration đứng đầu. Bằng chứng `image-index.json`, `image-integration.json`.

Ngày 2026-10-22 restart worker và gửi ảnh khác hash chưa cache qua frontend BFF: 46937.343ms, HTTP200, navy-sweater đầu (`image-cold-start.json`). Gồm lazy imports/load model và xử lý; vượt mục tiêu vài giây. Lượt trình duyệt ảnh đầu từng timeout; chạy lại đạt. UI báo lần đầu có thể gần một phút; timeout encoder55s nằm trong API60s, fallback văn bản có sẵn.

MIT Fashion-MNIST: gallery100 train, query20 test disjoint; actual CPU CLIP: hit@1=.85, hit@5/10=1, recall@10=.625, NDCG@10=.6788, uncached encoder p95=270.568ms. Ảnh thumbnail28×28, không phải smartphone/cross-view robustness, không benchmark end-to-end store trên20 query này. Failure IDs được giữ trong `fashion-mnist-eval.json`.

CaltechDATA CC-BY4.0: gallery50/query25 ảnh chụp đối tượng tách ID/bytes, 5 lớp có nhãn nguồn, top1=1.0, recall@10=0.872, NDCG@10=0.9116, uncached encoder p95=261.668ms. Đã xem contact sheet; query có khác nền/góc chụp nhưng không phải nghiên cứu camera điện thoại hay thời trang same-SKU. Không đưa ảnh benchmark vào public catalog. `photo-eval.json` giữ từng top10/manifest/attribution.

**HTTP ảnh đủ luồng:** `warm-image-http.json` đo25 ảnh hợp lệ khác hash, all cached=false sau warmup riêng; p95=429.857ms, p50=273.275ms trên catalog demo50 sản phẩm. Bao gồm sanitize/encoder/SQL/vector/ranking/serialize. Sửa2 pixel theo run chỉ để tránh cache, không dùng làm relevance metric. Ảnh nhỏ hơn5MB, không phải worst-case12MP. Warm target≤2.5s đạt trong lượt này. Timers image_encoder_http/image_embed/model_load lồng nhau, không cộng đôi; vector_search đã tách khỏi ranking.

## Giọng nói thật và audio tổng hợp bằng Whisper

**Đo người thật:** VIVOS20 giọng đọc/10 speakers, 1–12s, lựa chọn 2 mẫu đạt giới hạn đầu tiên mỗi speaker, không sửa/cắt waveform. WER=0.2392, CER=0.1200, HTTP p95=1877.518ms; `vivos-base.json`. Attribution Luong & Vu/AILAB-VNUHCM, CC-BY-NC-SA4.0, chỉ học thuật; corpus/audio nằm private. Không có nhãn miền, shopping, noise hoặc mixed English; không tuyên bố đại diện toàn bộ tiếng Việt. TC2: Đang chờ tệp âm thanh TC2; chưa có kết quả nghiệm thu nguyên câu từ giọng người dùng.

`voice-synthetic.json`: 6 renderings eSpeak của một câu; mean WER=0.8333, CER=0.4653, intent accuracy=0.0000. WER/CER có thể >1 do insertions/hallucinated repetitions; không chặn/cắt chỉ số để làm đẹp. Model load/inference/duration từng mẫu được ghi riêng. Không gọi synthetic voice variants là test người thật Bắc/Trung/Nam. Sau bước sửa câu, winter soft/áo phao đầu và modality voice được chứng minh qua browser; điều này không biến transcript sai thành ASR pass. Guard repetition được thêm; xem timestamp/source của evidence trước khi so sánh lần đo.

`voice-integration.json`: silence/corrupt/unsupported/16s từ chối422; median warm HTTP của sample135 riêng, không là p95 dân số. `ui/recording-results.json`: fake Chrome capture phát WAV tổng hợp; actual MediaRecorder→WebM→ASR, không micro vật lý. Đã có VIVOS20 human; chưa có bộ shopping/noise/numbers/mixed-language/vùng miền đại diện.

Chrome: install vi-VN thành công; probe headless nhận dạng chưa có transcript (language-not-supported/aborted hoặc không kết thúc). Vì vậy UI on-device là thử nghiệm, có timeout15s, không tự chuyển cloud. `ui/ondevice-results.json` chỉ chứng minh contract bằng callbacks giả lập, không nâng thành WER/CER thật. Xem INFERENCE_OPTIONS cho phương án miễn phí và tài nguyên.

### Giọng vùng miền và stress đã đo

ViMD: 3 đoạn/region có nhãn nguồn, giữ WAV nhận được nguyên trạng, không cắt/chuẩn hóa audio; chỉ đánh giá học thuật private, không tái phân phối audio/transcript (CC-BY-NC-ND4.0, Dinh et al., EMNLP2024). Dataset filter index lỗi500/timeout; dùng row windows có sẵn và một shard South≈463MB có SHA256. Không tải toàn corpus. `regional-voice.json`:

| Nhãn nguồn | Số mẫu | WER | CER |
|---|---:|---:|---:|
| North | 3 | 0.5070 | 0.2757 |
| Central | 3 | 0.6250 | 0.3728 |
| South | 3 | 0.7108 | 0.4488 |

Base nhận sai nhiều trên các mẫu tin tức này. Đây là smoke sample nhỏ, không phải độ chính xác dân số từng miền, không so sánh năng lực của nhóm người nói. Không nâng điểm sau sửa transcript. Độ dài/HTTP/inference từng đoạn được giữ trong JSON; first/cold/long clip không gọi là p95 warm5s.

`voice-stress.json`: 3 human waveforms với noise Gaussian seed42/SNR10dB, WER từng mẫu=[0.2857, 0.5, 0.2727]; 2 câu TTS có hoodie/size/giá chữ, WER=[1.2727, 0.8889]. WER>1 do chèn thêm từ được giữ nguyên. Noise tạo ra không đại diện nhiễu thật; câu tổng hợp không chứng minh tiếng Anh trộn/size đã nhận chính xác. Có số đo và failure cases, chưa tuyên bố ASR chất lượng cao.

## Trình duyệt và tài nguyên

Lượt gõ/focus thật ngắn, <50 interactions: largest EventTiming duration (ngưỡng ghi16ms) là 40ms ở1440px / 48ms ở360px. Đây chỉ là INP lab candidate trên lượt ngắn, không field/representative INP; raw entries trong JSON. null có nghĩa không quan sát entry≥16ms, không tự ghi0ms.

`browser-lab.json`: hai navigation local Chrome không throttling, LCP=376ms ở1440px và256ms ở360px, CLS=0/0; đây là sample, không field percentile. INP chưa đo bằng phiên tương tác đại diện. Screenshot desktop/mobile được xem trực tiếp. RSS/container stats là snapshot, không peak memory. Chi phí inference API ngoài=0; CPU/RAM/điện/hosting vẫn là tài nguyên có chi phí.
