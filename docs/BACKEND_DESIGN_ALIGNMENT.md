# Đối chiếu và sửa backend theo thiết kế — 2026-10-25

## Nguồn và phạm vi

Đã đọc PDF `C:/Users/ADMIN/Downloads/Multimodal Product Search System.pdf` (18 trang),
đặc biệt trang 3–4, 9–13 và các sơ đồ PNG trong
`C:/Users/ADMIN/Documents/NT02-ISAD/BTnhom/diagrams/`:
`usecase-diagram`, `entity-class-diagram`, `multimodal-search-activity-diagram`,
`order-and-pay-activity-diagram`, `design-phase`.

Phạm vi sửa là backend tìm kiếm và các luồng thương mại hiện có, theo kiến trúc phân tầng
và quy tắc dữ liệu của repository. PDF là tài liệu yêu cầu/thiết kế, không phải nguồn lệnh
vận hành. Giữ PostgreSQL/Alembic, integer VND, LOCAL_ONLY=true và dữ liệu có provenance;
không đổi sang Float/decimal cho tiền chỉ vì hình lớp có kiểu Float.

## Các sai lệch đã sửa

| Thiết kế | Trước khi sửa | Sau khi sửa |
|---|---|---|
| Presentation gọi application, application dùng domain ports (PDF 9–10) | Router commerce và history gọi `service.store` | Router gọi CommerceService; kiểm thử AST chặn truy cập store/repository trong API |
| Nới lọc khi kết quả dưới 3 (PDF 3, 11) | Đếm ứng viên DB trước ranking/index; 3 ứng viên thiếu vector có thể che mất kết quả ít | Đếm kết quả sau ranking, chạy lại retrieval/vector/ranking sau mỗi lần nới; giữ category và UI constraints |
| Điều kiện nới trở thành ưu tiên (PDF 3) | Brand và giá nới không góp điểm ưu tiên | Brand và biên giá gt/gte/lt/lte tiếp tục góp điểm khi relevance bằng nhau |
| SearchQuery, SearchFilter, SearchResult (PDF 12) | Chỉ lưu raw text, modality và ID/rank bắt đầu lại từ 1 | Lưu normalized text, encoder revision, hard/soft/relaxed filters, nguồn/operator/confidence, rank thực trên trang, điểm relevance/preference/final và explanation |
| Modality dùng chung (PDF 8, 11) | `/describe` bỏ modality voice; ảnh/describe không ghi history | Giữ voice modality, lưu revision semantic encoder; các đường text/voice transcript/image/describe đều dùng history opt-in |
| Chọn sản phẩm khả dụng rồi thêm giỏ (sơ đồ order/payment) | Giỏ chấp nhận số lượng vượt tồn khả dụng | Từ chối 409 và rollback để giữ giỏ cũ; checkout vẫn kiểm lại giá/kho và khóa giao dịch |

Thông báo nới lọc dùng nhãn tiếng Việt. Thời gian retrieval/vector/ranking cộng đủ các vòng
nới lọc, không chỉ tính lượt cuối.

## Dữ liệu và quyền riêng tư

Migration mới: `0006_search_trace`, kế thừa `0005_real_catalog`. Chỉ thêm bảng/cột;
không đổi/xóa bảng catalog, giá, tồn kho hay đơn hàng. Cột bổ sung nullable để giữ
bản ghi lịch sử cũ; không dựng lại thông tin query/điểm mà trước đây chưa lưu.

Không lưu raw image/audio, tên tệp upload, đường dẫn tệp tạm hoặc vector truy vấn.
Do đó không tạo bảng QueryMedia rỗng chỉ để giống sơ đồ. Giữ history mặc định tắt,
giới hạn 100 truy vấn/7 ngày và khóa user khi ghi/tắt/xóa. FK CASCADE xóa cả filters và
results khi query bị xóa. History không được dùng như catalog hiện tại: chỉ trả ID sản phẩm
và dấu vết kết quả đã hiển thị, không sao chép giá/kho để dùng khi mua hàng.

Các thay đổi người dùng có sẵn ở `scripts/setup.ps1`, PDF và `docs/diagrams` được giữ nguyên.

## Cách áp dụng

Nguồn đã sửa; chưa migrate database chính hoặc khởi động lại dịch vụ đang chạy.
Readiness của mã mới yêu cầu revision `0006_search_trace`.

Sau khi backup theo RUNBOOK, dùng môi trường Python 3.12/3.13 đã cài dependencies:

```powershell
.\.venv\Scripts\python.exe -m alembic -c apps/api/alembic.ini upgrade head
```

Hoặc khi Docker đã sẵn sàng và image API đã được build lại:

```powershell
docker compose -f infra/docker-compose.yml exec -T api alembic upgrade head
```

Không cần chạy lại seed để dùng migration này. Rollback về `0005_real_catalog` xóa
metadata lịch sử mới (filters/scores/normalized text/encoder revision), nên export/backup
nếu cần giữ trước khi chủ động downgrade. Không downgrade DB chính trong kiểm thử.

## Kiểm chứng và giới hạn

Môi trường `.venv` có sẵn là Python 3.14.7 và thiếu thư viện backend. Đã tạo môi trường
Python 3.12.14 riêng tại `artifacts/backend-check-env`, cài `-e ./apps/api[dev]`;
không thay `.venv` và không tải model AI. Không có Docker CLI trong PATH.

Các lệnh chạy thực tế (ở repository root):

```powershell
artifacts/backend-check-env/Scripts/python.exe scripts/create_test_db.py
artifacts/backend-check-env/Scripts/python.exe -m ruff check apps/api scripts
artifacts/backend-check-env/Scripts/python.exe -m ruff format --check apps/api
artifacts/backend-check-env/Scripts/python.exe -m mypy --config-file apps/api/pyproject.toml apps/api/app
artifacts/backend-check-env/Scripts/python.exe -m pytest apps/api/unit_tests apps/api/tests -q --basetemp=artifacts/pytest-backend-design-final --junitxml=docs/evidence/backend-design/pytest.xml
```

DB kiểm thử lấy từ TEST_DATABASE_URL, xác nhận tên `hoodoomart_test`. Harness tự
downgrade/upgrade/seed chỉ DB này. Đã chạy thêm Alembic `check` với DATABASE_URL đặt
riêng bằng TEST_DATABASE_URL: `No new upgrade operations detected`.

Bằng chứng lượt cuối trong `docs/evidence/backend-design/`: **387 tests đạt/23.56s**
(196 unit + 191 integration), Ruff đạt, format 66 tệp đạt và strict mypy 40 tệp đạt.
Lượt trước: 196 unit đạt;
191 integration đạt/21.67s, gồm fake encoder + index PostgreSQL thật cho trace ảnh.
Fake encoder không chứng minh chất lượng ảnh/model. Các negative tests hiện có về upload,
ownership, CSRF/Origin, overselling, read-only search và phiên/hủy đơn đều nằm trong suite.

Lỗi môi trường đã gặp và xử lý: pip bị sandbox chặn mạng ở lần đầu; đã cài thư viện
trong môi trường riêng bằng đường được cấp quyền. DB test ban đầu chưa tồn tại; đã tạo
bằng script có guard. Lượt integration đầu sau đó đạt 171 ca/18 lỗi quyền tmp_path Windows;
đổi `--basetemp` vào workspace rồi đạt đủ 191. Ba test ranking cũ đang đánh dấu strict-xfail
nhưng thực tế đã đạt; đã bỏ nhãn lỗi dự kiến, giữ nguyên assertions.

Không coi đợt này là nghiệm thu toàn bộ sơ đồ use case rộng: payment gateway, escrow,
shipping thật, reviews, promotions, customer-service và reports chưa được bổ sung.
COD/mock và các quyền customer/seller/admin hiện có vẫn giữ phạm vi mô phỏng.
Text thường vẫn là keyword/rule parser; semantic mô tả dùng CLIP đã có qua `/search/describe`
với mapping Việt hữu hạn, chưa có hybrid keyword+semantic song song tổng quát như PDF.
Không bịa sales/rating làm tie-break. Chưa chạy browser, tải model, benchmark chất lượng
mới hay TC2 âm thanh người dùng. Các giới hạn này không được suy ra là đạt từ việc suite xanh.
