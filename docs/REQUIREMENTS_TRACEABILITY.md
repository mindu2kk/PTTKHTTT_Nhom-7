# Nghiệm thu và nguồn yêu cầu

Số trang dưới đây được đọc trực tiếp từ `reference/PTTKHT-Slides.pdf`; chi tiết khác biệt tại SLIDE_AUDIT. E = quyết định kỹ thuật mới từ MD/triển khai.

| Ca/yêu cầu | Nguồn | Triển khai và bằng chứng | Kết luận |
|---|---|---|---|
| TC1: áo len nam đen <500k | PDF 18/50; MD §1 | `test_search.py`, `ui/m3-results.json`: 10 kết quả, 264000/324000/456000 | Đạt fixture, không tuyên bố dữ liệu Tiki |
| TC2: nói câu áo mùa đông | PDF 19/51 | ASR local thật, sửa câu, winter soft, áo phao đầu; `vivos-base.json`, `regional-voice.json`, `voice-stress.json`, `ui/m5-results.json`, `ui/recording-results.json` | Luồng chạy; **nguyên câu giọng người dùng chưa đạt nghiệm thu vì chờ tệp** |
| TC3: ảnh áo len xanh than | PDF 19/52 | CLIP thật, navy-sweater đứng đầu qua API/Chrome; `image-integration.json`, `ui/m4-results.json` | Đạt minh họa curated; chưa chứng minh ảnh điện thoại |
| TC4: túi đỏ <150k, mở rộng | PDF 20/53; E bảo vệ explicit text | strict 1, bấm đồng ý nới màu →3; đỏ 95000 đầu, 99000/149000 qua course-v2; `test_course_v2.py`, `ui/m3-results.json` | Đạt fixture có bước đồng ý, khác auto-relax slide đã công bố |
| TC5: đơn 20261005 | PDF 21/54 | `test_tc5_owner_and_tc6_read_only`, `ui/course-order.png`: CONFIRMED, 115500+595000=710500; người khác 404 cùng thông báo mã không tồn tại | Đạt với chủ sở hữu được gán bằng công cụ cục bộ |
| TC6: read-only business state | PDF 49; E privacy history | `test_search_readonly`, test order snapshot, `tc6-media-readonly.json`: text/voice/image/ASR thật không đổi 11 bảng nghiệp vụ | Đạt phạm vi kiểm thử; history riêng, opt-in, best-effort |
| Catalog/rights/provenance/category tree | PDF 7/10, MD §§4–6 | original CC0, negative cases, 4/11/34, recursion; `test_catalog.py`, dataset-audit | Đạt fixture; tên cây khác dữ liệu gốc slide |
| Auth/CSRF/IDOR | E MD security/P0 | Argon2id, session hash+expiry, HttpOnly, Origin+double-submit, owner filters; `test_commerce.py` | Đạt local |
| Stock/stale price/idempotency/cancel | E MD P1 | DB locks/atomic rollback, 2 buyers stock=1 → 201/409, duplicate same key →same order | Đạt local demo |
| Admin/seller CRUD/import review | E MD P0/P1 | own seller drafts, admin-only publish/import, JSON preview/QC, repeat-body reuse | Đạt mô phỏng có nguồn, external import quyền chưa rõ bị chặn |
| History privacy/retention | E MD P0 | opt-in false; delete/disable; max100; cutoff7d; hourly purge, không media | Đạt tests; physical expiry có thể trễ tối đa một chu kỳ giờ |
| Quality/performance | MD §§10–11 | 204 structured qrels/3k, HTTP Docker thật, Fashion-MNIST20 + Caltech25 ảnh held-out, VIVOS20 người thật và synthetic6, lab Chrome | Có số đo/phạm vi rõ; chưa phải human relevance/regional speech study |
| CPU deployment/repeat seed | E MD M7 | `clean-start.json`, full Compose frontend/API/DB/worker, four migrations | Đạt local; public production chưa nghiệm thu |

Không đánh dấu tất cả TC1–TC6 là đạt hoàn toàn: TC2 còn gate chất lượng; TC3 còn gate ảnh thực tế. Test transcript do người dùng sửa không phải bằng chứng nhận dạng nguyên câu chính xác.
