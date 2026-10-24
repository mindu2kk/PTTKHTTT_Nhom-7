# Nguồn, quyền dữ liệu và provenance

## M8 — nguồn catalog hiện tại

`DATA_PROFILE=real_demo`: Amazon Berkeley Objects (ABO), metadata và ảnh ©Amazon.com theo CC-BY-4.0, revision `listings_0-49304dd0edc3aa3d4cb19231927732fc`. Public318 sản phẩm/624 ảnh đã duyệt; 3 bản ghi QC giữ nháp. Giá/hạn mức đặt thử được cấu hình riêng và gắn nhãn mô phỏng, không phải dữ liệu thương nhân. Nguồn/license/attribution, SHA256/revision và quyết định đối với các nguồn khác tại [M8_DATASET_SOURCES](M8_DATASET_SOURCES.md); số thực tại [M8_DATASET_AUDIT](M8_DATASET_AUDIT.md).

Adapter ABO hỗ trợ quarantine → dry-run → kiểm mapping/ảnh → import danh sách đã duyệt → index tăng dần; manifest công khai ghi ID/URL/hash ở `evidence/m8/catalog-manifest.json`. Không dùng URL công khai làm giấy phép. CAMEO/ceyda/womensfashion đã được kiểm metadata/card trong M8, không được nhập public; xem lý do cụ thể ở tài liệu nguồn M8.

## Nguồn và lịch sử M0–M7

| Nguồn | Tình trạng thực tế | Quyền/sử dụng |
|---|---|---|
| catalog.json + 55 SVG tự tạo | 55 stored/50 public/5 negative; 49 danh mục; không phải Tiki | CC0-1.0, raw hash/source/batch/field provenance; giá/kho mô phỏng |
| course-v2.json | Bản hiệu chỉnh riêng: bag-navy125000→99000, bag-beige145000→149000 theo slide p53 | Manually authored CC0 demo; chỉ áp dụng nếu đúng old revision, raw v1 được giữ |
| PDF người dùng | 57 trang, bản gốc không sửa, copy nguyên `reference/PTTKHT-Slides.pdf` | Tài liệu bài học cục bộ; không coi slide là giấy phép tái xuất bản dataset/ảnh Tiki |
| OpenCLIP ViT-B/32 | Approved download, real CPU inference | Repo/revision/SHA256/size/MIT tại `evidence/model-manifest.json`; không external inference |
| faster-whisper base | Approved download, CPU int8, vi | Cùng manifest; quality của giọng tổng hợp yếu, không gán thành tích người thật |
| Fashion-MNIST | 100 gallery train +20 query test, disjoint; ảnh28×28 phóng224 | MIT repository, archive MD5 và LICENSE giữ trong `data/private/fashion-mnist`; class qrels không chứng minh same-product/smartphone retrieval |
| VIVOS | 20 bản ghi người thật giữ nguyên, 2 mẫu/người, 10 speakers; 84.96MB test parquet | [Nhóm AILAB/VNUHCM, Luong & Vu](https://zenodo.org/records/7068130), CC-BY-NC-SA4.0; chỉ benchmark học thuật cục bộ, nằm `data/private/vivos`, không public audio/catalog. Reference text và báo cáo mang cùng license/attribution |
| ViMD | 9 bản WAV nhận nguyên trạng, 3 mẫu/region North/Central/South theo nhãn nguồn | [Dinh/Dang/Nguyen/Nguyen, EMNLP2024](https://huggingface.co/datasets/nguyendv02/ViMD_Dataset), CC-BY-NC-ND4.0; audio và transcript ở private, không sửa/cắt/tái phân phối. Báo cáo công khai chỉ số/ID/hash. Source shard≈463MB, không tải toàn corpus |
| Voice stress | 3 VIVOS clips cộng Gaussian noise10dB +2 câu mua hàng eSpeak có số/hoodie/size XL | Phần VIVOS-derived CC-BY-NC-SA4.0, chỉ học thuật/private; không gọi noise tổng hợp là môi trường thật hoặc câu TTS là người nói thật |
| Caltech101 | 50 gallery/25 query ảnh đối tượng; 5 lớp camera/headphone/laptop/watch/umbrella | [CaltechDATA](https://data.caltech.edu/records/mzrjq-6wc02), CC-BY4.0; tác giả Fei-Fei Li, Marco Andreetto, Marc'Aurelio Ranzato, Pietro Perona; MD5/selection trong manifest, không import public store |
| Chrome vi-VN | Người dùng đồng ý 2026-10-22, cài gói trong hồ sơ kiểm thử tách riêng | Component do Chrome quản lý theo điều khoản Chrome, không gán MIT/CC0, không tái phân phối. Cài thành công không chứng minh nhận giọng headless đạt; xem INFERENCE_OPTIONS |
| eSpeak NG audio | WAV tổng hợp câu TC2, 3 synthetic voice variants×2 speeds | Dự án tự sinh từ câu kiểm thử; tên Northern/Central/Southern của synthesizer không phải nhãn người nói thật |
| 3k scale corpus +204 qrels | Clone fixture gốc trong DB `_test`, xóa exact run IDs sau đo | Synthetic structured oracle, không human judgments và không dữ liệu thương mại thật |
| FLEURS vi | Đã kiểm tra card CC-BY4; chưa tải audio | Rows endpoint trả500 scan limit691MB; không coi là bộ test đã có. [Dataset card](https://huggingface.co/datasets/google/fleurs) |
| Tiki/CAMEO/FashionSmall/WomensFashion/VNFashion và ảnh merchant khác | Chưa thu thập, chưa được duyệt để publish | Không suy ra quyền từ URL công khai. Không scraper vượt chặn/không nhập unknown-rights vào catalog |

Luồng quản lý M6 ở profile demo_seed hỗ trợ JSON nguyên bản do operator xác nhận CC0 và dùng ảnh gốc đã duyệt; bản ghi luôn là nháp cho tới admin duyệt. Adapter ABO của M8 được ghi ở phần đầu; các nguồn khác vẫn cần map source IDs, license/allowed_use, quarantine/QC rồi review; không dùng historical source price làm offer hiện tại.

Uploaded ảnh/audio của người dùng chỉ ở bộ nhớ xử lý tạm; không vào `data/private`, gallery hoặc database. Bench audio/image cố định là tài sản kiểm thử đã nêu nguồn, không phải bản ghi người dùng bị giữ lại.
