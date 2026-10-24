"""Build concise current-state handoff from saved, actually measured evidence."""

# ruff: noqa: E501
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_json(name):
    return json.loads((ROOT / "docs/evidence" / name).read_text(encoding="utf-8-sig"))


def put(name, body):
    (ROOT / name).write_text(body.strip() + "\n", encoding="utf8")


def main():
    scale = read_json("scale-3000.json")
    voice = read_json("voice-synthetic.json")
    image = read_json("fashion-mnist-eval.json")
    cold = read_json("image-cold-start.json")
    human = read_json("vivos-base.json")
    photos = read_json("photo-eval.json")
    browser = read_json("browser-lab.json")
    http_scale = read_json("scale-3000-http.json")
    warm_image = read_json("warm-image-http.json")
    regional = read_json("regional-voice.json")
    stress = read_json("voice-stress.json")
    tc2_file = ROOT / "docs/evidence/tc2-user-audio.json"
    tc2 = read_json("tc2-user-audio.json") if tc2_file.exists() else None
    tc2_status = (
        "Đạt trên file người dùng, không sửa transcript"
        if tc2 and tc2["result"] == "passed"
        else "Đang chờ tệp âm thanh TC2; chưa có kết quả nghiệm thu nguyên câu từ giọng người dùng"
    )
    verification = (ROOT / "docs/evidence/final-verification.txt").read_text(
        encoding="utf8"
    )
    matches = re.findall(r"(\d+) passed", verification)
    tests = matches[-1] if matches else "pending final run"
    durations = re.findall(r"passed in ([\d.]+)s", verification)
    test_seconds = durations[-1] if durations else "unknown"
    put(
        "README.md",
        r"""
# HoodooMart

Ứng dụng khám phá sản phẩm tiếng Việt, chạy cục bộ bằng Docker và CPU. Đã đọc slide 57 trang; đối chiếu tại [SLIDE_AUDIT](docs/SLIDE_AUDIT.md).

**Đã có:** storefront responsive; tìm văn bản và bộ lọc có nguồn gốc; CLIP tìm ảnh thật; Whisper chép giọng nói thật với bước sửa câu; đăng ký/đăng nhập; giỏ tài khoản; COD/thanh toán mô phỏng; tra đơn riêng tư; giữ/nhả tồn kho; lịch sử tự chọn; quản lý và nhập bản nháp có kiểm duyệt.

**Đã đo thêm:** Whisper trên 20 bản ghi người thật/10 người nói VIVOS, 9 bản ghi ViMD có nhãn ba miền và 5 ca stress; CLIP trên 25 ảnh đối tượng giữ riêng khỏi 50 ảnh gallery CaltechDATA; 3k sản phẩm qua HTTP thật Docker. Xem BENCHMARKS cho số liệu/phạm vi. Nhận giọng trên thiết bị là tùy chọn thử nghiệm, luôn processLocally=true, chỉ cài gói sau khi bấm; kiểm thử callback không phải bằng chứng chất lượng nhận dạng.

**Giới hạn cần biết:** chưa nhận được tệp giọng thật nguyên câu TC2 của người dùng; mẫu ba miền nhỏ và ASR còn nhận sai nhiều. Ảnh catalog demo vẫn là SVG gốc; benchmark ảnh đối tượng không chứng minh same-product/thời trang/ảnh điện thoại. Tải cao và khởi động model lạnh có giới hạn. Đây là bản thực hành cục bộ; production và semantic text model không phải tính năng được tuyên bố đã chạy.

## Chạy nhanh — PowerShell 7, tại thư mục gốc

Yêu cầu Docker Desktop Linux engine và Python 3.12/3.13 cho công cụ phát triển. Chạy frontend bằng Docker không cần Node cài trên máy.

```powershell
.\scripts\setup.ps1
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait
docker compose --env-file .env -f infra/docker-compose.yml exec -T api python -m app.infrastructure.seed
docker compose --env-file .env -f infra/docker-compose.yml exec -T api python -m app.infrastructure.course_fixture
```

Mở [HoodooMart](http://localhost:3000) hoặc [API](http://localhost:8000/docs). Compose tự chạy migration. Seed lặp lại không ghi đè tồn kho/giá đã sửa. Bản hiệu chỉnh course-v2 giữ nguyên raw v1, chỉ đổi hai giá túi theo slide nếu đúng phiên bản gốc; có khác biệt sẽ dừng.

Tìm ảnh/giọng nói cần trọng số ở `models/` (đã tải trong phiên làm việc này sau khi được cho phép). Máy mới: đọc dung lượng/giấy phép trong RUNBOOK, chỉ chạy lệnh tải sau khi đồng ý. Không có API suy luận trả phí, tải ngầm hoặc thanh toán thật.

```powershell
# Chỉ khi cần tải lại đúng các trọng số đã duyệt:
.\.venv\Scripts\python.exe scripts/download_models.py
.\.venv\Scripts\python.exe scripts/index_images.py
# Kiểm thử PostgreSQL riêng và khởi động sạch:
.\scripts\verify.ps1
.\scripts\verify-clean.ps1
```

Tạo tài khoản trong giao diện. Quản trị/người bán và việc gán đơn mẫu `20261005` dùng lệnh cục bộ, mật khẩu nhập ẩn:

```powershell
.\.venv\Scripts\python.exe scripts/provision_account.py --email ban@example.invalid --role customer --bind-fixture-order
.\.venv\Scripts\python.exe scripts/provision_account.py --email quantri@example.invalid --role admin
```

Không có tài khoản admin/mật khẩu mặc định. Không đăng `.env`, `models/`, `artifacts/` hay `data/private/` lên Git. Không chạy `downgrade base`/xóa volume chính để sửa lỗi.

## Tài liệu bàn giao

- [Tiến độ và bằng chứng](docs/PROGRESS.md) · [Lệnh vận hành](docs/RUNBOOK.md) · [Kịch bản demo](docs/DEMO.md)
- [Nghiệm thu theo slide](docs/REQUIREMENTS_TRACEABILITY.md) · [Số đo và giới hạn](docs/BENCHMARKS.md)
- [Kiến trúc](docs/ARCHITECTURE.md) · [25 bảng dữ liệu](docs/DATA_DICTIONARY.md) · [API](docs/API_CONTRACTS.md)
- [Nguồn/giấy phép](docs/DATA_SOURCES.md) · [Quyết định](docs/DECISIONS.md) · [Bảo mật](docs/SECURITY.md)
- [Lựa chọn nhận giọng miễn phí và tài nguyên](docs/INFERENCE_OPTIONS.md) · [Checklist chốt M7](docs/M7_COMPLETION_AUDIT.md)

50 sản phẩm công khai từ 55 fixture gốc; 49 danh mục (4/11/34), tên cây khác dữ liệu Tiki của slide. Không tuyên bố đã thu được 1.148 sản phẩm Tiki. Tính toán vẫn dùng CPU/RAM/điện; hosting/storage có thể phát sinh chi phí.
""",
    )
    put(
        "docs/PROGRESS.md",
        f"""
# Tiến độ hiện tại

Cập nhật ngày 2026-10-22; giữ nguyên ngày đo trong từng bằng chứng.

## Completed

- M0–M1: đọc MD/PDF, đối chiếu trực tiếp, schema/migration/seed gốc có provenance và quyền dữ liệu.
- M2–M4: Next.js tiếng Việt, URL filters/facets thật, giỏ, text parser và relaxation có đồng ý; OpenCLIP CPU thật, pgvector được lọc trước theo quyền/danh mục/giá.
- M5: ghi âm/dừng/hủy/nhả micro, tải audio, Whisper base cục bộ và câu sửa đi qua chung pipeline. Đã thêm nhận giọng trên thiết bị, feature detection, cài gói có đồng ý, không tự chuyển cloud, watchdog15s và fallback. VIVOS20 người thật/10 người nói: WER={human["wer"]:.4f}, CER={human["cer"]:.4f}. **{tc2_status}.**
- M6: Argon2id, phiên băm/HttpOnly, CSRF+Origin, owner lookup và universal order intent; giỏ server; checkout giao dịch/idempotency; hủy/nhả kho; admin/seller RBAC; nhập JSON xem trước rồi tạo nháp/duyệt; lịch sử mặc định tắt, tối đa 100 câu/7 ngày.
- M7: giới hạn raw/chunked body trước parser tại BFF/API/worker; single-job CPU; rate/deadline; Docker frontend/API/PostgreSQL/worker; clean-start harness; kiểm thử/bằng chứng và tài liệu bàn giao.

## Changed files

`apps/api` domain/application/SQL/API commerce, speech/media, 4 Alembic revisions; `apps/inference`; `apps/web` storefront/auth/order/manage/voice/image; `infra/docker-compose.yml`; công cụ `scripts/`; bộ kiểm thử `benchmarks/scripts/`; bản course-v2 giữ raw v1; tài liệu và bằng chứng trong `docs/`.

## Tests run and exact results

Lượt kiểm tra cuối: **{tests} passed trong {test_seconds}s**; output đầy đủ `evidence/final-verification.txt`, JUnit `evidence/pytest.xml`. Ruff, strict mypy 35 application files, Alembic schema check; build/lint frontend và các luồng Chrome thật được ghi riêng. `evidence/clean-start.json` là kết quả khởi động Docker DB riêng, seed/revision lặp lại, BFF CSRF đăng ký/đặt/hủy; không xóa volume chính.

Lệnh đã chạy: `scripts/verify.ps1`, `scripts/verify-clean.ps1`, `scripts/browser_verify.py e2e_storefront e2e_text e2e_image e2e_voice read_only_audit browser_lab`, `benchmarks/scripts/e2e_commerce.py`, `benchmarks/scripts/e2e_recording.py`, `benchmarks/scripts/scale_eval.py`, `benchmarks/scripts/voice_synthetic_eval.py`, frontend ESLint và Docker Compose build/up. Kết quả PostgreSQL sau sửa khóa history/session: 10 test commerce đạt; bằng chứng riêng `commerce-final-followup.txt`.

Lượt trình duyệt đầu bị timeout khi chờ kết quả ảnh; lượt regression cuối đạt cả 9 nhóm (`browser-final-run.json`). Kiểm tra khởi động worker lạnh, query ảnh chưa cache qua BFF trả200/navy đầu trong {cold["http_ms"] / 1000:.3f}s (`image-cold-start.json`). Tăng timeout encoder trong giới hạn API60s và báo thời gian tải lần đầu trên UI; không coi cold latency này là đạt mục tiêu.

Sau build cuối, regression 9 nhóm đạt trên Docker. Lượt media trước đó được giữ riêng (`media-postbuild.json`). `final-build.txt` trích output build thành công và bốn dịch vụ healthy; log đầy đủ tại `artifacts/last-build.log` được bỏ qua khi quản lý mã nguồn.

Lượt hoàn thiện mới: `evidence/browser-final-run.json` chứa regression Docker các luồng trang chủ/text/ảnh/voice/ghi âm/commerce/TC6; `ui/ondevice-results.json` là UI/provider callbacks giả lập được ghi nhãn rõ. `bff-upload-guards.json`: HTTP thật trả413 cho biểu mẫu quá lớn; hai chunked body không kết thúc trả408 sau khoảng15s. SQL bỏ predicate nối dư đã được composite FK bảo đảm, hash tập nguồn bị cấm một lần, UNION chống cây category giao nhau; không giảm kiểm tra quyền/giá/kho.

Bằng chứng giao diện: `evidence/ui/m2-results.json`, `m3-results.json`, `m4-results.json`, `m5-results.json`, `m6-results.json`, `recording-results.json`. Mẫu microphone trong recording harness là thiết bị Chrome mô phỏng phát WAV tổng hợp; MediaRecorder/WebM/Whisper phía sau là thật. Không gọi đây là kiểm thử micro vật lý.

## Benchmarks actually measured

3.000 sản phẩm mô phỏng, 204 câu có đáp án cấu trúc độc lập với parser, 612 lượt tìm + 300 lượt grid tại concurrency 1/5/10; `evidence/scale-3000.json`. Không dùng DB chính. Precision@10/NDCG@10 theo các oracle cấu trúc đạt 1, không chứng minh chất lượng ngữ nghĩa trên dữ liệu người dùng. Tất cả số đo độ trễ, ảnh, ASR và RAM trong BENCHMARKS; không gộp cache-hit với suy luận mới.

## Known limitations

TC2 nguyên câu: {tc2_status}. VIVOS là giọng đọc, không có nhãn ba miền/noise. Đã đo riêng ViMD9 có nhãn vùng và 5 ca stress; mẫu nhỏ, ASR còn yếu, chưa đại diện giọng mua hàng/nhiễu thực tế. 25 ảnh đối tượng Caltech không thay thế ảnh điện thoại/thời trang same-SKU. Chrome cài gói thành công trong hồ sơ test nhưng probe nhận dạng headless chưa trả transcript, nên on-device vẫn thử nghiệm. Chỉ một variant/offer/ảnh chính mỗi product; semantic model và public production không thuộc phần đã triển khai. 3k corpus/qrels còn mô phỏng; latency tải cao xem số đo, không cam kết SLA. 9 cảnh báo npm dev, audit runtime0. Không có cổng thanh toán/vận chuyển/escrow thật.

## Next implementation task

Chạy `benchmarks/scripts/voice_acceptance.py <file-audio>` khi tệp thực sự được gửi, không sửa transcript để làm đẹp kết quả. Không tải Whisper small theo hướng người dùng ưu tiên ít tài nguyên. Mở rộng ảnh điện thoại và mẫu giọng mua hàng/nhiễu thực tế khi có nguồn và quyền; production/P2 cần phạm vi mới. Không đánh dấu TC2 nguyên câu đạt khi chưa có file.
""",
    )
    put(
        "docs/IMPLEMENTATION_PLAN.md",
        """
# Kế hoạch và trạng thái M0–M7

Đã thực hiện theo thứ tự; nguồn chính là MD và PDF 57 trang trong `reference/`. Đối chiếu trang tại SLIDE_AUDIT; trạng thái thực tế tại PROGRESS, không dùng mô tả M1 cũ làm hiện trạng.

| Mốc | Kết quả triển khai | Gate còn mở |
|---|---|---|
| M0 | Audit, kiến trúc, traceability, nguồn, runbook | Không |
| M1 | PostgreSQL/25 bảng qua 4 migration, fixture gốc, quyền/provenance | Gate local đạt; một offer/variant/ảnh chính là phạm vi demo |
| M2 | Storefront/API, responsive, SSR/404/cart, form Zod | Gate browse/cart đạt; field INP không được tuyên bố |
| M3 | Text/parser/hard filters/soft ranking/consent-safe relaxation | TC1/TC4 đạt; semantic/hybrid là lựa chọn chưa triển khai |
| M4 | OpenCLIP thật/offline/QC; 25 ảnh đối tượng held-out + Fashion-MNIST | TC3 curated đạt; chưa chứng minh ảnh điện thoại/same-SKU thời trang |
| M5 | MediaRecorder/Whisper, VIVOS20 + ViMD9 + 5 ca stress, thử nghiệm on-device | Chờ tệp TC2 nguyên câu của người dùng; ASR còn yếu, mẫu nhỏ |
| M6 | Auth/ownership/cart/transaction/admin/import/history | Thanh toán/vận chuyển thật thuộc P2 |
| M7 | CPU Compose, regression, 3k/204 oracle + HTTP thật, security, handoff | Phần kỹ thuật đã kiểm; chưa đóng toàn bộ gate TC1–TC6 vì chờ TC2; không yêu cầu production/P2 |

## Quyết định phạm vi

- Giữ modular monolith, một worker inference CPU; không thêm Redis/Kubernetes/GPU vì chưa có bằng chứng cần thiết.
- Giữ tên HoodooMart; dữ liệu gốc do dự án tạo, không nhận là Tiki.
- TC4: màu văn bản giữ cứng cho tới khi người dùng cho phép nới; category/UI không nới. Course-v2 hiệu chỉnh hai giá có kiểm tra phiên bản, không ghi đè thay đổi người dùng.
- Hoàn thiện tính đúng/quyền/transaction trước chất lượng model và trang trí. Chất lượng model không được suy ra từ việc tải được weights hoặc tạo được pipeline.
""",
    )
    put(
        "docs/REQUIREMENTS_TRACEABILITY.md",
        """
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
""",
    )
    put(
        "docs/ARCHITECTURE.md",
        """
# Kiến trúc hiện tại

Modular monolith: Next.js → same-origin BFF → FastAPI → PostgreSQL; một worker CPU riêng cho OpenCLIP/Whisper. Không có API suy luận từ xa, Redis hay GPU bắt buộc.

## Phân lớp

`api/v1 → application → domain`; infrastructure triển khai ports; `core/dependencies.py` ghép dịch vụ. Test AST chặn router nhập SQL repository và domain/application nhập framework/infrastructure. Query/Commerce/Media ports có thể thay provider.

## Tìm kiếm chung

Text hoặc transcript đã sửa → NFC/accent shadow/aliases/prices → QueryRepresentation (origin/operator/confidence) → SQL lọc quyền, publication, category subtree, giá/thuộc tính → lexical hoặc allowed-ID exact cosine → ranking ổn định → phân trang. Category/UI không nới; explicit text chỉ nới sau đồng ý. Giới hạn 1000 candidate, có thông báo khi chạm trần. Không có semantic text encoder/LLM trong bản này.

Ảnh: validate nội dung/MIME/extension/5MB/12MP → RGB/re-encode bỏ metadata → encode512D đúng revision → pgvector chỉ trong candidate đã lọc và đúng hash/revision. Vectors gallery tạo offline; cache5 phút/max100 chỉ chứa vector query, không chứa tệp gốc. Revalidate giá/kho hiện tại mỗi lần tìm.

Giọng: ghi tối đa12s ở browser, server nhận≤15s/2MB; PyAV decode mono16k trong worker; Whisper base int8 vi; trả metadata/warnings → sửa câu → cùng search service với modality voice. Không tự tìm ngay khi nhận xong bản chép lời. Ghi âm/hủy/navigation đóng tracks và ObjectURL.

## Auth và giao dịch

- Argon2id qua bounded threads; token phiên ngẫu nhiên, chỉ SHA256 trong DB, expiry7d, cookie HttpOnly/SameSite Lax. CSRF double-submit + Origin allowlist cho ghi nghiệp vụ; BFF kiểm origin. Secure cookie bật khi dùng HTTPS; mặc định loopback HTTP.
- Owner lookup luôn `orders.user_id=actor.id`, mã không tồn tại và người khác cùng404. Order intent không rơi sang product search sau thất bại. Không có admin mặc định; cấp role/gán order mẫu qua CLI nhập mật khẩu ẩn.
- Giỏ server không giữ kho. Checkout khóa user để serialize idempotency; khóa offer/inventory theo thứ tự ID; kiểm lại public/price/stock, ghi order/items/reservations/mock payment/shipment trong một transaction. Khác body cùng key →409.
- Hủy trước SHIPPED nhả held một lần. SHIPPED trừ on_hand và reserved, chuyển consumed; status progression có gate. Không có thanh toán/escrow thật.
- Seller chỉ sửa draft/offer mình; thay đổi seller cần duyệt lại; admin duyệt quyền/ảnh trước publish. Import JSON≤20 bản, xem trước kiểm category/image; nhập thành nháp; lặp exact body tái dùng raw hash trong cùng nguồn operator. Một batch provenance cho mỗi bản ghi.

## Dữ liệu và vận hành

25 bảng trong DATA_DICTIONARY, revision head `0004_commerce`. [ERD](diagrams/catalog-erd.svg), [nguồn Mermaid](diagrams/catalog-erd.mmd). Một variant/offer/ảnh chính mỗi product là giới hạn có UNIQUE thực tế; không gọi đây là marketplace multi-seller đầy đủ.

History mặc định tắt, chỉ text/transcript sau tìm; background task best-effort ngoài response, max100/user. API đọc lọc/purge7 ngày; maintenance giờ xóa quá hạn và sessions. Không lưu raw audio/image, không log bodies/querystrings/secrets. Search không ghi bảng nghiệp vụ.

Raw/chunked body có bound trước multipart ở BFF/API/worker; SQL3s, request5s hoặc60s media; inference một job, busy429; giới hạn tốc độ theo process local. Docker ports chỉ127.0.0.1; frontend/API/inference non-root; web read-only filesystem/cache tmpfs. Current DB role là owner phát triển; xem SECURITY cho giới hạn production.

P2 payment/carrier/finance/dispute chỉ có domain Protocol trong `domain/integrations.py`; chưa có live adapter.
""",
    )
    put(
        "docs/DATA_DICTIONARY.md",
        """
# Dữ liệu hiện tại — 25 bảng

Schema do Alembic quản lý, head `0004_commerce`; không create_all runtime. VND BIGINT, số lượng integer. PostgreSQL vector/pg_trgm/unaccent được cài qua migration.

| Bảng | Nội dung/khóa và bất biến |
|---|---|
| data_sources | revision/license/rights/allowed_use/check time; demo/approved/unknown/restricted |
| import_batches | source FK, counts/errors/status/time; nháp→duyệt/lưu trữ |
| source_products | PK(source_id,external_id), raw JSON/SHA256/batch; giữ raw v1 khi course-v2 thêm provenance |
| categories | unique slug, self parent FK, level≥0; recursion không giới hạn3 tầng |
| products | unique slug, original/vi text, category/brand/gender, profile/publication/review, search shadow |
| product_sources | composite raw-record FK; mọi nguồn phải có quyền, không chỉ một nguồn tốt |
| product_attributes | PK(product,key), canonical/display/review/provenance/confidence0–100 |
| product_images | unique product FK; storage key có index và có thể tái dùng ảnh CC0 đã duyệt; hash/size/license/alt |
| product_variants | unique product/SKU; size/color/options/status; một variant/product |
| seller_offers | unique product/variant; composite variant/product FK; integer price>0/kind; seller verified+active |
| inventory | offer PK/FK; 0≤reserved≤on_hand; version tăng theo biến động |
| users | email unique, nullable Argon2 hash, active, history_opt_in=false; fixture owner disabled |
| user_roles | PK(user,role), role customer/seller/admin; không nhận role từ form đăng ký |
| seller_profiles | user FK/PK, approved=false; chỉ operator cấp hồ sơ demo được duyệt |
| sessions | SHA256 token PK, user FK, expiry index; raw token chỉ trong cookie |
| carts | user PK/FK, timestamp; không reserve stock |
| cart_items | PK(user,product), qty1–99; validated cart≤50 lines |
| orders | unique code, owner FK, status/total/profile/address/time; unique(owner,idempotency_key), request hash |
| order_items | name/price purchase snapshots, positive qty/price, order/product FKs |
| stock_reservations | PK(order,offer), qty>0, held/released/consumed; nhả/consume đúng một lần |
| mock_payments | order PK/FK, cod/mock, pending/simulated_paid/cancelled; không lưu card |
| shipments | order PK/FK, local_demo provider, status mô phỏng |
| search_queries | owner FK/text≤300/modality/time, opt-in, max100, TTL7d+purge tối đa1h |
| search_results | PK(query,product), rank; cascade khi xóa query; không dùng làm sold/rating giả |
| image_embeddings | PK(image,model,revision), 512D vector/content hash/time; không trộn text vectors |

FK đơn hàng/source hạn chế xóa để giữ bằng chứng; sessions/role/history/cart children cascade theo quan hệ đã khai báo. Xóa lịch sử không xóa order hay tồn kho. Migration downgrade trên dữ liệu có storage key trùng/deep category có thể bị chặn bởi UNIQUE/CHECK cũ; không xóa dữ liệu để ép rollback. Backup và xem RUNBOOK trước thao tác schema thật.
""",
    )
    put(
        "docs/API_CONTRACTS.md",
        """
# API hiện tại

Nguồn máy đọc: `openapi.json` (export bằng `scripts/export_openapi.py`); TypeScript sinh tại `apps/web/src/lib/schema.ts`. Browser gọi `/api/v1` qua Next BFF; API gốc loopback8000.

| Nhóm | Endpoint | Quyền/bất biến |
|---|---|---|
| Catalog | GET categories, facets, products, products/{id_or_slug} | Public, chỉ approved/demo đúng profile; paging≤24; category subtree/price/color/gender/material/brand/size; no-store |
| Text | GET/POST search/text | q≤300, modality text/voice; hard/soft/relaxed origins/operators; products hoặc order discriminated response |
| Suggest | GET search/suggestions | q2–100; tối đa5; không lưu history |
| Image | POST search/image multipart image + filters/text/page | ≤5MB JPEG/PNG/WebP, decode/re-encode; same SearchResponse + media metadata |
| Voice | POST search/voice multipart audio | ≤2MB,≤15s, WAV/WebM/Ogg/M4A thực; TranscriptResponse với revision/duration/timing/warnings; chưa tự search |
| Auth | GET auth/csrf; POST auth/register/login/logout; GET auth/me | Form unsafe cần cookie/header CSRF + Origin; HttpOnly session7d; registration chỉ customer |
| Cart | GET/PUT cart | Owner, items product_id+quantity; không tin giá client, không giữ kho |
| Checkout | POST checkout | Owner+CSRF; Idempotency-Key16–80; address/method cod/mock/items expected_price; atomic revalidation, stale409 |
| Orders | GET orders; GET orders/{code}; PATCH orders/{code} | GET owner only; không tồn tại/người khác404 giống nhau; customer cancel trước shipped, admin status progression |
| History | GET/PATCH/DELETE history | Owner; opt-in mặc định false; disable/delete xóa; 100/7d; không media |
| Manage | GET manage/products, manage/images; POST manage/products; PATCH manage/products/{id}; POST manage/products/{id}/publish,archive | Seller own approved profile; chỉ admin publish; shared approved CC0 image library |
| Import | POST manage/imports/preview; POST manage/imports | Admin, records≤20 DraftBody; manual original-data affirmation; preview category/image errors; nháp, không auto publish |
| Health | GET health/live, health/ready | Ready kiểm schema0004, không lộ DB URL |

SearchResponse `search_type=products`: query/items(rank,score,explanation)/total/page/stages/engine/notices. Order response `search_type=order`: order, không có product results. Search score là heuristic relevance, không phải xác suất tin cậy. Order intent từ chối quyền không được fallthrough.

Lỗi JSON tiếng Việt: 401 chưa đăng nhập, 403 quyền/CSRF/Origin, 404 generic private lookup, 409 price/stock/idempotency/state, 413 raw upload limit, 422 input/decode, 429 busy/rate, 503 model/DB unavailable, 504 deadline. Request ID/no-store/nosniff; không trả stack/SQL/password. BFF forward Set-Cookie, không forward arbitrary host/path ra internet.

BFF chặn body không kết thúc sau15s bằng408, kể cả chunked và form không JavaScript; dùng cùng helper boundedBody, không chờ vô hạn trước lúc fetch API.
""",
    )
    put(
        "docs/DATA_SOURCES.md",
        """
# Nguồn, quyền dữ liệu và provenance

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

Import hiện hỗ trợ JSON nguyên bản do operator xác nhận CC0 và dùng ảnh gốc đã duyệt; bản ghi luôn là nháp cho tới admin duyệt. Không giả vờ đã có source adapter của bốn dataset ngoài. Khi có dữ liệu thật, cần map source IDs, license/allowed_use, quarantine/QC rồi review; không dùng historical source price làm offer hiện tại.

Uploaded ảnh/audio của người dùng chỉ ở bộ nhớ xử lý tạm; không vào `data/private`, gallery hoặc database. Bench audio/image cố định là tài sản kiểm thử đã nêu nguồn, không phải bản ghi người dùng bị giữ lại.
""",
    )
    put(
        "docs/SECURITY.md",
        """
# Bảo mật và giới hạn vận hành

## Đã triển khai và kiểm thử

- Argon2id và bounded hashing; session random token/hash/expiry; HttpOnly/SameSite, logout revoke, login rotate.
- CSRF double-submit + Origin cho ghi nghiệp vụ, BFF same-origin; strict input fields không nhận role/admin từ registration.
- Owner filter cho order/history/cart; 404 khác chủ giống mã không tồn tại; universal order intent không fallthrough.
- Giá/kho authoritative trong transaction; ordered row locks; idempotency hash; cancel/release/consume một lần.
- Publication/verification/all-source rights/image rights/offer guards trong SQL; exact vector lookup chỉ được allowed IDs hiện tại và revision/hash đúng.
- Body limits trước multipart kể cả chunked tại BFF/API; worker giới hạn stream; raster whitelist/decompression bound/strip metadata; audio whitelist/no video/time/sample limits; không lưu raw upload.
- CPU single inference job, fail-fast429; local per-process rate caps; SQL/request deadlines; safe errors/no secrets in logs; loopback-only ports và non-root services.
- Optional history max100/7d, hourly maintenance, disable/delete; media không lưu. CSP/nosniff/frame denial/referrer/permissions headers ở frontend.

## Audit dependency thực tế

`evidence/npm-runtime-audit.json`: 0 reported runtime vulnerabilities. shadcn là công cụ dev/build, không phải dependency chạy ứng dụng. `evidence/npm-full-audit.json`: 9 high trong cây công cụ dev liên quan braces/glob; không có bản vá upstream theo [advisory GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm). Không downgrade shadcn/Next bằng audit --force; công cụ dev chỉ chạy trên mã/pattern nội bộ tin cậy. Đây không phải tuyên bố toàn bộ supply chain không có lỗi.

## Chưa nghiệm thu production

DB role hiện là local owner để migration/demo thuận tiện; chưa tách migration/API least privilege. HTTP chỉ loopback, Secure cookie=false cho local; public HTTPS cần TLS/COOKIE_SECURE/origin/secret/backup-restore cấu hình và kiểm thử theo môi trường thật. CSP còn unsafe-inline cho Next hydration, không tuyên bố CSP nonce chặt. Rate limit theo một process, BFF gom client IP; không dùng X-Forwarded-For tùy ý làm nguồn tin. Không public host, payment/card/carrier/escrow thật, không password reset/email service hoặc production SLA.

Giữ `.env`, weights, private data và artifacts ngoài Git. Không dùng downgrade base/xóa volume main để sửa lỗi; kiểm tra phiên bản và backup trước thay đổi thật.
""",
    )
    rows = "\n".join(
        f"| {r['concurrency']} | {r['service_ms']['p50']} | {r['service_ms']['p95']} | {r['http_asgi_ms']['p95']} |"
        for r in scale["runs"]
    )
    grids = "\n".join(
        f"| {r['concurrency']} | {r['http_asgi_ms']['p95']} |"
        for r in scale["grid_runs"]
    )
    put(
        "docs/BENCHMARKS.md",
        f"""
# Số đo thật và giới hạn

Máy: Intel Core i3-1315U, 8 logical processors, RAM15.73GiB, Windows11 Pro; DB/worker trong Docker Linux, worker CPU threads2, không GPU. `evidence/hardware.json`. Các lần đo khác nhau có thể chịu contention build/ASR; không gọi số đo một lần là SLA.

## 3.000 sản phẩm, 204 câu tiếng Việt

2950 clone fixture +50 public gốc, tổng3005 stored; DB `_test` riêng, không reset main, dọn exact run IDs trong finally. 34 leaf×6 dạng câu: có/không dấu, lời mua, giá số/giá chữ và màu. Đáp án category/color/price viết theo cấu trúc fixture, **không phải human semantic judgments**. Từng lượt dùng API native qua HTTPX ASGITransport + PostgreSQL thật: gồm validation/serialize/SQL, không gồm TCP/uvicorn network overhead. Warm10 trước mỗi nhóm; 204 request/nhóm, concurrency1/5/10. Qrels: `benchmarks/qrels/synthetic-204.json`.

| Đồng thời | Service p50 ms | Service p95 ms | ASGI HTTP p95 ms |
|---:|---:|---:|---:|
{rows}

Precision@10=1, NDCG@10=1, Recall@10≈0.11349, hard-filter leaks=0 theo các oracle cấu trúc. Recall thấp vì mỗi leaf có khoảng86–100 relevant items còn K=10; không diễn giải như chất lượng nhận diện sản phẩm thực. Lượt đầu phát hiện búp bê→be và tối đa→da; đã sửa/parser test; trước sửa lưu `scale-before-parser-fix.json`. EXPLAIN thấy estimated1/actual3000, đã ANALYZE sau bulk import thay vì thêm ANN/GIN thiếu bằng chứng. Before/after và plan JSON giữ trong evidence; không khẳng định ANALYZE luôn nhanh hơn.

Grid: 100 request/nhóm, 10 trang luân phiên:

| Đồng thời | ASGI HTTP p95 ms |
|---:|---:|
{grids}

Không có hybrid semantic≤900ms claim. Số đo HTTP qua TCP trên fixture55 gốc nằm riêng `text-benchmark.json`/`catalog-benchmark.json`, không gộp với 3k.

Lượt tối ưu mới đạt text service≤300ms ở c1/c5, chưa đạt c10; grid ASGI≤400ms ở c1/c5. Đã chuyển source bị cấm thành tập ID hashable, nối offer→variant bằng FK thay vì lặp điều kiện product, UNION cho cây giao nhau. Composite FK vẫn chặn offer sai product. EXPLAIN grid giảm khoảng51k xuống478 shared buffer hits, actual startup≈46ms; trước sửa giữ tại `scale-plan-before-rights-optimization.json`. Không thay đổi quyền/giá/stock để cải thiện số đo.

### HTTP thật trên Docker — số đo triển khai cục bộ

`scripts/benchmark-http.ps1` mở API riêng cổng8002 dùng DB `hoodoomart_test`, giữ cùng corpus 3k/204 queries; đo Windows HTTPX→TCP loopback→Docker API Python3.12→PostgreSQL. Không chạy build/ASR trong lượt cuối; API benchmark được stop/remove sau đo. `scale-3000-http.json`; lượt bị contention build giữ riêng `scale-http-during-build.json`, không gộp chọn số đẹp.

| Đồng thời | Search service p95 ms | Search TCP p95 ms | Grid TCP p95 ms |
|---:|---:|---:|---:|
{chr(10).join(f"| {r['concurrency']} | {r['service_ms']['p95']} | {r['http_tcp_ms']['p95']} | {g['http_tcp_ms']['p95']} |" for r, g in zip(http_scale["runs"], http_scale["grid_runs"], strict=True))}

Target là mục tiêu đo, không SLA; mức10 đồng thời còn giới hạn. Qrels HTTP riêng `synthetic-204-http.json`; IDs scale đã được dọn đúng run, không reset dữ liệu main.

## Ảnh thật bằng OpenCLIP

M4 offline50 gallery:39.824s, model load20.022s, RSS snapshot976.59MiB. API query đầu2800.551ms trong worker đã dùng để tạo chỉ mục; cache-hit repeat p95129.739ms **không phải uncached inference**. Curated navy illustration đứng đầu. Bằng chứng `image-index.json`, `image-integration.json`.

Ngày 2026-10-22 restart worker và gửi ảnh khác hash chưa cache qua frontend BFF: {cold["http_ms"]}ms, HTTP200, navy-sweater đầu (`image-cold-start.json`). Gồm lazy imports/load model và xử lý; vượt mục tiêu vài giây. Lượt trình duyệt ảnh đầu từng timeout; chạy lại đạt. UI báo lần đầu có thể gần một phút; timeout encoder55s nằm trong API60s, fallback văn bản có sẵn.

MIT Fashion-MNIST: gallery100 train, query20 test disjoint; actual CPU CLIP: hit@1=.85, hit@5/10=1, recall@10=.625, NDCG@10=.6788, uncached encoder p95={image["inference_p95_ms"]}ms. Ảnh thumbnail28×28, không phải smartphone/cross-view robustness, không benchmark end-to-end store trên20 query này. Failure IDs được giữ trong `fashion-mnist-eval.json`.

CaltechDATA CC-BY4.0: gallery50/query25 ảnh chụp đối tượng tách ID/bytes, 5 lớp có nhãn nguồn, top1={photos["metrics"]["hit1"]}, recall@10={photos["metrics"]["recall10"]}, NDCG@10={photos["metrics"]["ndcg10"]}, uncached encoder p95={photos["uncached_encoder_p95_ms"]}ms. Đã xem contact sheet; query có khác nền/góc chụp nhưng không phải nghiên cứu camera điện thoại hay thời trang same-SKU. Không đưa ảnh benchmark vào public catalog. `photo-eval.json` giữ từng top10/manifest/attribution.

**HTTP ảnh đủ luồng:** `warm-image-http.json` đo25 ảnh hợp lệ khác hash, all cached=false sau warmup riêng; p95={warm_image["percentiles_ms"]["p95"]}ms, p50={warm_image["percentiles_ms"]["p50"]}ms trên catalog demo50 sản phẩm. Bao gồm sanitize/encoder/SQL/vector/ranking/serialize. Sửa2 pixel theo run chỉ để tránh cache, không dùng làm relevance metric. Ảnh nhỏ hơn5MB, không phải worst-case12MP. Warm target≤2.5s đạt trong lượt này. Timers image_encoder_http/image_embed/model_load lồng nhau, không cộng đôi; vector_search đã tách khỏi ranking.

## Giọng nói thật và audio tổng hợp bằng Whisper

**Đo người thật:** VIVOS20 giọng đọc/10 speakers, 1–12s, lựa chọn 2 mẫu đạt giới hạn đầu tiên mỗi speaker, không sửa/cắt waveform. WER={human["wer"]:.4f}, CER={human["cer"]:.4f}, HTTP p95={human["http_p95_ms"]}ms; `vivos-base.json`. Attribution Luong & Vu/AILAB-VNUHCM, CC-BY-NC-SA4.0, chỉ học thuật; corpus/audio nằm private. Không có nhãn miền, shopping, noise hoặc mixed English; không tuyên bố đại diện toàn bộ tiếng Việt. TC2: {tc2_status}.

`voice-synthetic.json`: 6 renderings eSpeak của một câu; mean WER={voice["mean_wer"]:.4f}, CER={voice["mean_cer"]:.4f}, intent accuracy={voice["intent_accuracy"]:.4f}. WER/CER có thể >1 do insertions/hallucinated repetitions; không chặn/cắt chỉ số để làm đẹp. Model load/inference/duration từng mẫu được ghi riêng. Không gọi synthetic voice variants là test người thật Bắc/Trung/Nam. Sau bước sửa câu, winter soft/áo phao đầu và modality voice được chứng minh qua browser; điều này không biến transcript sai thành ASR pass. Guard repetition được thêm; xem timestamp/source của evidence trước khi so sánh lần đo.

`voice-integration.json`: silence/corrupt/unsupported/16s từ chối422; median warm HTTP của sample135 riêng, không là p95 dân số. `ui/recording-results.json`: fake Chrome capture phát WAV tổng hợp; actual MediaRecorder→WebM→ASR, không micro vật lý. Đã có VIVOS20 human; chưa có bộ shopping/noise/numbers/mixed-language/vùng miền đại diện.

Chrome: install vi-VN thành công; probe headless nhận dạng chưa có transcript (language-not-supported/aborted hoặc không kết thúc). Vì vậy UI on-device là thử nghiệm, có timeout15s, không tự chuyển cloud. `ui/ondevice-results.json` chỉ chứng minh contract bằng callbacks giả lập, không nâng thành WER/CER thật. Xem INFERENCE_OPTIONS cho phương án miễn phí và tài nguyên.

### Giọng vùng miền và stress đã đo

ViMD: 3 đoạn/region có nhãn nguồn, giữ WAV nhận được nguyên trạng, không cắt/chuẩn hóa audio; chỉ đánh giá học thuật private, không tái phân phối audio/transcript (CC-BY-NC-ND4.0, Dinh et al., EMNLP2024). Dataset filter index lỗi500/timeout; dùng row windows có sẵn và một shard South≈463MB có SHA256. Không tải toàn corpus. `regional-voice.json`:

| Nhãn nguồn | Số mẫu | WER | CER |
|---|---:|---:|---:|
{chr(10).join(f"| {name} | {g['samples']} | {g['wer']:.4f} | {g['cer']:.4f} |" for name, g in regional["groups"].items())}

Base nhận sai nhiều trên các mẫu tin tức này. Đây là smoke sample nhỏ, không phải độ chính xác dân số từng miền, không so sánh năng lực của nhóm người nói. Không nâng điểm sau sửa transcript. Độ dài/HTTP/inference từng đoạn được giữ trong JSON; first/cold/long clip không gọi là p95 warm5s.

`voice-stress.json`: 3 human waveforms với noise Gaussian seed42/SNR10dB, WER từng mẫu={[round(r["wer"], 4) for r in stress["results"][:3]]}; 2 câu TTS có hoodie/size/giá chữ, WER={[round(r["wer"], 4) for r in stress["results"][3:]]}. WER>1 do chèn thêm từ được giữ nguyên. Noise tạo ra không đại diện nhiễu thật; câu tổng hợp không chứng minh tiếng Anh trộn/size đã nhận chính xác. Có số đo và failure cases, chưa tuyên bố ASR chất lượng cao.

## Trình duyệt và tài nguyên

Lượt gõ/focus thật ngắn, <50 interactions: largest EventTiming duration (ngưỡng ghi16ms) là {browser["samples"][0].get("inp_lab_candidate_ms")}ms ở1440px / {browser["samples"][1].get("inp_lab_candidate_ms")}ms ở360px. Đây chỉ là INP lab candidate trên lượt ngắn, không field/representative INP; raw entries trong JSON. null có nghĩa không quan sát entry≥16ms, không tự ghi0ms.

`browser-lab.json`: hai navigation local Chrome không throttling, LCP={browser["samples"][0]["lcp_ms"]}ms ở1440px và{browser["samples"][1]["lcp_ms"]}ms ở360px, CLS={browser["samples"][0]["cls"]}/{browser["samples"][1]["cls"]}; đây là sample, không field percentile. INP chưa đo bằng phiên tương tác đại diện. Screenshot desktop/mobile được xem trực tiếp. RSS/container stats là snapshot, không peak memory. Chi phí inference API ngoài=0; CPU/RAM/điện/hosting vẫn là tài nguyên có chi phí.
""",
    )
    put(
        "docs/DEMO.md",
        r"""
# Kịch bản demo theo slide

## Chuẩn bị

Chạy quickstart README, course-v2 và `scripts/index_images.py`; tạo tài khoản riêng trong UI. Đơn mẫu `20261005` chỉ xem được sau lệnh local `provision_account.py --email ... --bind-fixture-order`; nhập ẩn mật khẩu, không có tài khoản mặc định. Không gán đơn người khác: CLI chỉ cho order mẫu chưa có chủ.

1. Mở localhost:3000, xem nhãn dữ liệu mô phỏng, danh mục, chi tiết/VND/tồn kho và giỏ.
2. **TC1:** nhập `áo len nam màu đen dưới 500k` →10, giá đầu264000/324000/456000; xem hard chips. Thử `ao len nam den duoi 500 nghin`.
3. **TC2:** vào Giọng nói, cho phép micro và nói `tôi muốn mua áo mùa đông`; xem/nghe bản ghi, bấm chuyển chữ; kiểm tra/sửa câu rồi tìm. Winter là ưu tiên mềm, áo phao đầu. Công bố rõ: Whisper base chưa đạt gate giọng thật; không phát file TTS rồi gọi là người nói thật.
4. **TC3:** tải `benchmarks/images/navy-sweater-heldout.png` vào Hình ảnh →navy sweater cạnh tranh đầu; thử thêm danh mục/giá và reload URL. Đây là minh họa held-out gốc, không ảnh smartphone.
5. **TC4:** nhập `túi đeo chéo màu đỏ dưới 150k` →1. Bấm “Cho phép mở rộng màu” →3, đỏ95000 đầu; hai giá khác99000/149000 theo course-v2. Giải thích bước đồng ý thêm so với slide để bảo vệ điều kiện người dùng.
6. **TC5:** đăng nhập đúng chủ, nhập `kiểm tra đơn hàng 20261005` →order CONFIRMED,115500+595000=710500. Mở bằng tài khoản khác →thông báo chung không tìm thấy, không lộ order.
7. **TC6:** chạy read_only_audit.py và pytest: business-state hashes không đổi khi tìm; lịch sử chỉ lưu riêng khi opt-in. Không dùng việc click search như thao tác reserve.
8. Thêm sweater còn kho →cart→COD/mock checkout→đơn CONFIRMED→hủy. Giá/stock đổi sẽ409 để kiểm tra lại; retry cùng key không tạo đơn trùng.
9. Tài khoản→bật lịch sử→tìm→xem/xóa/tắt. Admin local→quản lý→tạo/nhập JSON nháp→kiểm duyệt→publish. Người bán không tự publish.

## Lỗi có chủ ý cần trình bày

Từ chối micro →nhập text/tải audio; ảnh hỏng/HEIC/oversize →thông báo; model busy/unavailable →thử lại hoặc text; query không liên quan→empty; out-of-stock thấy được nhưng không thêm giỏ. Không bịa rating/sold, carrier/payment live hoặc dữ liệu Tiki.
""",
    )
    put(
        "docs/DECISIONS.md",
        r"""
# Quyết định đang áp dụng

1. PDF đã đọc trực tiếp, 57 trang; nguồn và số trang tại SLIDE_AUDIT. Tên HoodooMart là thay đổi thương hiệu; không tự thay nghiệp vụ slide.
2. Giữ fixture CC0 gốc 4/11/34, không tự nhận tên cây/dataset Tiki gốc. Course-v2 là bản hiệu chỉnh hai giá riêng, có old-revision guard; không sửa raw v1/không ghi đè offer đã được người dùng đổi.
3. Category và UI-selected luôn hard; explicit text chỉ nới khi có đồng ý. TC4 thêm bước consent, công bố khác slide auto-relax.
4. Lexical/rule text baseline được chọn để giữ CPU/chi phí đơn giản; không gọi nó là AI hay semantic/hybrid. Giới hạn1000 candidate được thông báo. Không thêm GIN/HNSW khi chưa có plan/recall chứng minh cần.
5. OpenCLIP và Whisper base được tải sau consent, pinned revisions/digests/MIT; một CPU worker, một job chung. Không model trong mỗi API worker, không paid/vendor speech API.
6. Whisper base chạy thật nhưng không được tuyên bố đạt chất lượng từ mẫu TTS. Repetition guard và bản chép lời sửa được là cơ chế bảo vệ, không phải thay thế đánh giá giọng người thật. Tin nhắn câu TC2 của người dùng nhận được dưới dạng text, không có audio waveform để chấm ASR.
7. Auth opaque server session/hash/Argon2 thay vì JWT dài hạn; CSRF+Origin và private owner filtering. Admin/seller chỉ cấp bằng local CLI, không default public credential.
8. Checkout mock/COD, row locks và idempotency; không card/escrow thật. Reserve ở checkout, không ở cart/search. Chỉ consume khi ship, cancel trước ship nhả một lần.
9. History opt-in false, max100/7d; ghi background best-effort. Opt-out và history writer khóa cùng user để không để lại bản ghi sau khi tắt; hourly physical purge.
10. Cookie chứa guest IDs/qty; giỏ lớn vượt ngưỡng cookie dùng localStorage có marker. Logout xóa dữ liệu guest; server vẫn kiểm toàn bộ giá/kho/quyền. Không raw media trong cookie/history.
11. Full CPU Compose là cách chạy chính. Native frontend cần Node24; image Node24.13.0, API Python3.12.12; native Python3.13 là môi trường phát triển phụ. Chỉ bind loopback, chưa public deployment.
12. shadcn CLI thuộc dev/build dependency; audit runtime0, full dev9high chưa có upstream patch. Không dùng audit --force để downgrade framework. P2 payment/carrier/finance/dispute chỉ là Protocol, không live adapter.
""",
    )
    put(
        "docs/RUNBOOK.md",
        r"""
# Vận hành — PowerShell 7

Chạy ở thư mục gốc `D:\PTTKHT WEB ecommerce`. Docker Desktop Linux engine. Docker là đường chạy đầy đủ; native tools cần Python3.12/3.13 và frontend Node24. Không đọc/in `.env` vào log.

## Khởi động và dữ liệu

```powershell
.\scripts\setup.ps1
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait
docker compose --env-file .env -f infra/docker-compose.yml exec -T api alembic upgrade head
docker compose --env-file .env -f infra/docker-compose.yml exec -T api python -m app.infrastructure.seed
docker compose --env-file .env -f infra/docker-compose.yml exec -T api python -m app.infrastructure.course_fixture
Invoke-RestMethod http://localhost:8000/health/ready
```

Mở localhost:3000 (API docs8000). Host ports: DB55432, API8000, web3000, worker19090. Windows loại trừ port9000 nên worker host dùng19090; nội bộ9000. Đổi WEB_PORT/API_PORT trong Compose tự đổi Origin allowlist; health check gửi external Host hợp lệ bằng Node http. BFF không so Origin với hostname0.0.0.0 nội bộ Docker.

Seed additive, raw drift bị từ chối; course-v2 lặp an toàn nhưng sẽ dừng nếu offer không còn đúng phiên bản mong đợi. DATA_PROFILE=approved_public không công khai fixture demo. Setup tạo secret ngẫu nhiên khi chưa có `.env`, không ghi đè file có sẵn.

## Trọng số và chỉ mục ảnh

Đã có consent cho OpenCLIP≈605MB + Whisper base≈145MB; CPU libraries/container tải thêm, tổng vài GB đĩa. Trọng số pinned repo/revision/SHA256/MIT ở `docs/evidence/model-manifest.json`. Chỉ chạy download khi đã đồng ý; setup/compose không tự tải model. Máy hiện tại đã có weights.

```powershell
.\.venv\Scripts\python.exe scripts/download_models.py
.\.venv\Scripts\python.exe scripts/index_images.py
Invoke-RestMethod http://localhost:19090/health
```

Index chạy offline cho products published/rights-safe, kiểm source image hash, dùng đúng CLIP revision. Sau admin publish mới, chạy index lại. Không encode toàn gallery trong mỗi query. Models mount read-only; lazy load lúc request đầu. Health phân biệt file có và model đã load; thiếu model vẫn dùng text, media trả503/fallback. Không thay weights cùng tên rồi giả metadata revision cũ.

## Tài khoản, vai trò và đơn mẫu

```powershell
.\.venv\Scripts\python.exe scripts/provision_account.py --email ban@example.invalid --role customer --bind-fixture-order
.\.venv\Scripts\python.exe scripts/provision_account.py --email quantri@example.invalid --role admin
.\.venv\Scripts\python.exe scripts/provision_account.py --email nguoiban@example.invalid --role seller
```

Password getpass, không argv/stdout/default credential. Existing account được đổi password rõ ràng bằng lệnh operator này; role seller tạo approved demo profile. Gán đơn20261005 chỉ khi owner là disabled fixture hoặc cùng user; nếu đã thuộc người khác, từ chối. Đăng nhập UI rồi `/account/orders`, `/orders/lookup` hoặc câu `kiểm tra đơn hàng 20261005`. Cấp admin xong vào `/manage`. Không dùng dữ liệu cá nhân thật trong demo.

## Nhập danh mục

UI quản lý chọn ảnh đã duyệt; import JSON chỉ admin, max20, bấm preview rồi confirm tạo draft. Mỗi bản ghi có source/raw hash/batch; exact body lặp tái dùng bản ghi dưới khóa user, không nhân đôi. Publish tách riêng sau review. Ví dụ JSON (thay image_id bằng ID từ `GET /api/v1/manage/images`):

```json
[{"name":"Áo len mô phỏng mới","description":"Mô tả nguyên bản do người vận hành tạo","category_id":"ao-len-nam","image_id":"THAY_BANG_ID_ANH_DA_DUYET","price_vnd":200000,"stock":8,"color":"đen","material":"len","size":"M","original_data_confirmed":true}]
```

Không arbitrary image URL, không public unknown-rights, không coi imported source price là giá merchant thật. Bản này chỉ hỗ trợ demo original; source adapter ngoài cần quyền và quarantine riêng.

## Kiểm thử và hợp đồng

```powershell
.\scripts\verify.ps1
.\scripts\verify-clean.ps1
.\.venv\Scripts\python.exe data_pipeline/audit.py --output docs/evidence/dataset-audit.json
.\.venv\Scripts\python.exe scripts/export_openapi.py
```

verify: Ruff/format/strict mypy/Alembic check/test DB/pytest. TEST_DATABASE_URL phải kết thúc `_test`; chỉ DB đó bị down/up và seed. Không chạy đồng thời pytest và scale_eval vì dùng cùng test DB. verify-clean tạo project/volume riêng, tự chọn4 cổng loopback trống qua OS để tránh dải bị Windows loại trừ; cổng thực được ghi trong clean-start.json. Full stack, repeat seed+course-v2, BFF auth/checkout/cancel rồi dọn project đó; không chạm volume main và khôi phục biến môi trường trước khi chạy.

Frontend native (Node24 có sẵn trong runtime Codex của máy này; máy khác cài Node24 hoặc dùng Docker):

```powershell
$taskNode='C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
.\.venv\Scripts\python.exe scripts/export_openapi.py
Push-Location apps/web
& $taskNode node_modules/openapi-typescript/bin/cli.js ../../docs/openapi.json -o src/lib/schema.ts
& $taskNode node_modules/eslint/bin/eslint.js src
& $taskNode node_modules/next/dist/bin/next build
Pop-Location
# Chỉ dùng native web khi đã stop service web để trống3000:
docker compose --env-file .env -f infra/docker-compose.yml stop web
.\scripts\start-web.ps1
.\scripts\stop-web.ps1
```

Fresh native node_modules: chạy npm ci bằng npm CLI dưới Node24 tại apps/web (không dùng wrapper npm.ps1 trỏ Node22 cũ của máy này). Docker build tự npm ci đúng Node24.13.0. OpenAPI types là generated, không sửa tay.

Native API: giữ PostgreSQL, stop API container để trống8000; root `.env` đọc host DB55432.

```powershell
docker compose --env-file .env -f infra/docker-compose.yml stop api
.\.venv\Scripts\python.exe -m alembic -c apps/api/alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

## Chrome và benchmark thật

Chrome đã cài; Python Playwright nằm trong dev dependencies. Các script dùng channel chrome headless, không cần tự tải Chromium. Chạy stack đầy đủ trước:

```powershell
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_storefront.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_text.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_image.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_voice.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_ondevice.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_recording.py
.\.venv\Scripts\python.exe benchmarks/scripts/e2e_commerce.py
.\.venv\Scripts\python.exe benchmarks/scripts/read_only_audit.py
.\.venv\Scripts\python.exe benchmarks/scripts/browser_lab.py
.\.venv\Scripts\python.exe benchmarks/scripts/scale_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/text_benchmark.py
.\.venv\Scripts\python.exe benchmarks/scripts/image_integration.py
.\.venv\Scripts\python.exe benchmarks/scripts/voice_integration.py
.\.venv\Scripts\python.exe benchmarks/scripts/voice_synthetic_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/fashion_mnist_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/photo_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/warm_image_api.py
.\.venv\Scripts\python.exe benchmarks/scripts/vivos_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/regional_voice_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/voice_stress_eval.py
.\.venv\Scripts\python.exe benchmarks/scripts/bff_guards.py
.\scripts\benchmark-http.ps1
# Khi người dùng thực sự gửi tệp âm thanh:
.\.venv\Scripts\python.exe benchmarks/scripts/voice_acceptance.py 'D:\duong-dan\ban-ghi.wav'
```

E2E commerce tạo account browser ngẫu nhiên, setup owner fixture có guard, restore owner bằng atexit; tạo order mới rồi cancel, không thu tiền. Không log password. Recording test là fake audio device + real recorder/ASR, không micro vật lý. ASR synthetic và Fashion-MNIST có nguồn/giới hạn riêng tại DATA_SOURCES/BENCHMARKS. Scale tạo2950 row run-scoped trong `_test` và xóa exact IDs trong finally, không reset main. Đọc kết quả thật, không coi script exit là chứng minh chất lượng người dùng.

Benchmark dữ liệu ngoài là lệnh chủ động, không chạy trong setup/app: VIVOS tải≈85MB; Caltech≈137MB; ViMD lần đầu≈463MB một shard, rồi tái dùng9 WAV private có kiểm SHA256. ViMD không tái phân phối/cắt audio; noise derivative chỉ dùng VIVOS cho phép share-alike. Tất cả nằm data/private, không tự publish vào catalog. API dataset có thể đổi/lỗi; ghi lỗi, không giả metrics khi chưa có dữ liệu.

## Quan sát, lỗi và dừng

```powershell
docker compose --env-file .env -f infra/docker-compose.yml ps
docker compose --env-file .env -f infra/docker-compose.yml logs --tail 20 api inference web
docker stats --no-stream
docker compose --env-file .env -f infra/docker-compose.yml stop
```

DB fail: xem migrate/ready và secret khớp volume, không xóa volume. 503 model: kiểm file/manifest/worker health; 429 đợi worker rảnh; text vẫn là fallback. Port conflict: kiểm process sở hữu và `netsh interface ipv4 show excludedportrange protocol=tcp` trước khi đổi. Cổng clean3001 bị Windows loại trừ trong lần chạy2026-10-22; script nay chọn động và đã chạy lại. Không bật native web và Docker web cùng3000.

Schema main không down/base tự động; downgrade có thể bị chặn để bảo vệ dữ liệu deep category/shared image key. Backup trước sửa schema; backup/restore production chưa được nghiệm thu. Public TLS, Secure cookies, migration/API role separation và host/origin khác cần cấu hình/kiểm thử mới, không mở host0.0.0.0 từ bản local rồi gọi production-ready.
""",
    )
    checks = read_json("browser-final-run.json")["checks"]
    put(
        "docs/M7_COMPLETION_AUDIT.md",
        f"""
# Checklist chốt M7 — 2026-10-22

## Trạng thái

Đã triển khai và kiểm thử kỹ thuật tới M7. **Chưa ghi tất cả gate đạt:** {tc2_status}. Semantic text model, public production và P2 thanh toán/vận chuyển thật không được tuyên bố đã chạy.

| Ca | Kết quả thực tế | Bằng chứng |
|---|---|---|
| TC1 | 10 áo len đen, giá đầu264000/324000/456000, hard filters đúng | test_search.py; ui/m3-results.json |
| TC2 | ASR thật/ghi âm/sửa câu/common pipeline đã chạy; {tc2_status} | vivos-base.json; voice-synthetic.json; ui/m5-results.json; ui/recording-results.json |
| TC3 | CLIP thật, navy sweater đầu ở fixture held-out minh họa; có benchmark đối tượng chụp độc lập | image-integration.json; ui/m4-results.json; photo-eval.json |
| TC4 | Strict1→3 sau đồng ý nới màu; đỏ95000 đầu, hai giá99000/149000 | test_course_v2.py; ui/m3-results.json; khác auto-relax slide đã ghi quyết định |
| TC5 | Owner thấy CONFIRMED/710500; anonymous/khác chủ bị chặn, không fallthrough | test_commerce.py; ui/m6-results.json; course-order.png |
| TC6 | Text/voice/image/ASR thật không đổi11 bảng nghiệp vụ; history opt-in riêng | tc6-media-readonly.json; các snapshot tests |

## Completed / Changed files

SQL repository tối ưu theo EXPLAIN, giữ quyền nguồn và composite FK; UNION chống cây danh mục giao nhau nhân đôi. Tách vector timer khỏi ranking. Thêm OnDeviceSpeech/browser-speech port, cài gói có đồng ý, local-only và timeout/cancel/fallback. BFF/form giỏ dùng chung boundedBody15s, kiểm cookie shape/qty/duplicate. Clean-start chọn cổng trống tránh Windows exclusions. Thêm HTTP Docker benchmark, VIVOS human, ảnh chụp đối tượng và warm full image path; cập nhật tài liệu/bằng chứng.

## Tests run and exact results

- verify.ps1: **{tests} passed/{test_seconds}s**; Ruff/format, strict mypy35 application files, Alembic check đạt (`evidence/final-verification.txt`).
- Chrome: **{sum(c["exit_code"] == 0 for c in checks)}/{len(checks)} nhóm đạt**: {", ".join(c["check"] for c in checks)} (`browser-final-run.json`).
- Clean Docker: migration/seed2 lần/course-v2/auth/checkout/cancel đạt (`clean-start.json`). Lượt đầu cổng3001 bị Windows chặn; đã sửa chọn cổng và chạy lại, không xóa main volume.
- BFF HTTP thật: quá bound413, cookie sai422, form no-JS hợp lệ303, chunked body không kết thúc408≈15s (`bff-upload-guards.json`).
- Callback on-device giả lập có nhãn riêng; Chrome cài gói thật nhưng probe headless chưa trả transcript. Không dùng simulation làm bằng chứng nhận dạng thật.

## Benchmarks actually measured

- 3k/204 qrels cấu trúc, HTTP Docker service p95={http_scale["runs"][0]["service_ms"]["p95"]}/{http_scale["runs"][1]["service_ms"]["p95"]}/{http_scale["runs"][2]["service_ms"]["p95"]}ms tại c1/5/10, zero filter leaks. Không phải bộ human semantic judgments.
- Full image HTTP warm/không cache vector p95={warm_image["percentiles_ms"]["p95"]}ms/25 ảnh. Caltech25 query khác50 gallery: recall@10={photos["metrics"]["recall10"]}, NDCG@10={photos["metrics"]["ndcg10"]}; không chứng minh same-SKU/thời trang/phone.
- VIVOS20 bản ghi/10 người thật: WER={human["wer"]:.4f}, CER={human["cer"]:.4f}, HTTP p95={human["http_p95_ms"]}ms. Giọng đọc mẫu nhỏ, chưa đại diện ba miền/noise.

- ViMD9 nguyên trạng có nhãn3 miền +3 noise cases và2 mixed-term TTS đã đo; WER/CER/failure đều giữ trong regional-voice.json/voice-stress.json. Base còn nhận sai nhiều, không đánh dấu chất lượng cao.

## Known limitations / Next implementation task

Chạy voice_acceptance.py khi người dùng gửi tệp thật để kiểm transcript chưa sửa→winter soft→áo phao đầu. Chrome on-device còn thử nghiệm theo browser; Whisper vẫn là local adapter thật. Không tải Whisper small, không gọi API trả phí. Target tải10 còn giới hạn; cold model≈47s, không dùng cache hit giả thành inference mới. Quyền và phạm vi corpus/ảnh/giọng được ghi rõ trong BENCHMARKS/DATA_SOURCES; không gọi bản local là production.
""",
    )
    print("Current-state handoff updated from saved evidence.")


if __name__ == "__main__":
    main()
