# API hiện tại

Nguồn máy đọc: `openapi.json` (export bằng `scripts/export_openapi.py`); TypeScript sinh tại `apps/web/src/lib/schema.ts`. Browser gọi `/api/v1` qua Next BFF; API gốc loopback8000.

| Nhóm | Endpoint | Quyền/bất biến |
|---|---|---|
| Catalog | GET categories, facets, products, products/{id_or_slug} | Public, chỉ approved/demo đúng profile; paging≤24; category subtree/price/color/gender/material/brand/size; no-store |
| Text | GET/POST search/text | q≤300, modality text/voice; hard/soft/relaxed origins/operators; products hoặc order discriminated response |
| Suggest | GET search/suggestions | q2–100; tối đa5; không lưu history |
| Mô tả | POST search/describe JSON | SearchRequest + mode visual/keyword; q1–300, paging≤24; SearchResponse; visual dùng text tower OpenCLIP512D cục bộ, mapping hữu hạn, bộ lọc cứng trước cosine; unknown/order intent422; model bận429/không sẵn503; deadline60s |
| So sánh | POST search/compare JSON ids | 2–3 ID duy nhất, mỗi ID1–100 ký tự; đọc lại public catalog theo profile; trả products/lowest_price_ids/notice; missing/không public404 chung; không tạo giao dịch hoặc truy cập đơn |
| Image | POST search/image multipart image + filters/text/page | ≤5MB JPEG/PNG/WebP, decode/re-encode; same SearchResponse + media metadata |
| Voice | POST search/voice multipart audio | ≤2MB,≤15s, WAV/WebM/Ogg/M4A thực; TranscriptResponse với revision/duration/timing/warnings và suggestions (mặc định[]); text được NFC/trim/gộp whitespace,1–300 ký tự, giữ nguyên từ nhận được; gợi ý cụm sản phẩm hữu hạn cần chọn xác nhận, chưa tự search |
| Auth | GET auth/csrf; POST auth/register/login/logout; GET auth/me | Form unsafe cần cookie/header CSRF + Origin; HttpOnly session7d; registration chỉ customer |
| Cart | GET/PUT cart | Owner, items product_id+quantity; không tin giá client, không giữ kho |
| Checkout | POST checkout | Owner+CSRF; Idempotency-Key16–80; address/method cod/mock/items expected_price; atomic revalidation, stale409 |
| Orders | GET orders; GET orders/{code}; PATCH orders/{code} | GET owner only; không tồn tại/người khác404 giống nhau; customer cancel trước shipped, admin status progression |
| History | GET/PATCH/DELETE history | Owner; opt-in mặc định false; disable/delete xóa; 100/7d; không media |
| Manage | GET manage/products, manage/images; POST manage/products; PATCH manage/products/{id}; POST manage/products/{id}/publish,archive | Seller own approved profile; chỉ admin publish; shared approved CC0 image library |
| Import | POST manage/imports/preview; POST manage/imports | Admin, records≤20 DraftBody; manual original-data affirmation; preview category/image errors; nháp, không auto publish |
| Health | GET health/live, health/ready | Ready kiểm schema0005, không lộ DB URL |

SearchResponse `search_type=products`: query/items(rank,score,explanation)/total/page/stages/engine/notices. Order response `search_type=order`: order, không có product results. Search score là heuristic relevance, không phải xác suất tin cậy. Order intent từ chối quyền không được fallthrough.

Lỗi JSON tiếng Việt: 401 chưa đăng nhập, 403 quyền/CSRF/Origin, 404 generic private lookup, 409 price/stock/idempotency/state, 413 raw upload limit, 422 input/decode, 429 busy/rate, 503 model/DB unavailable, 504 deadline. Request ID/no-store/nosniff; không trả stack/SQL/password. BFF forward Set-Cookie, không forward arbitrary host/path ra internet.

BFF chặn body không kết thúc sau15s bằng408, kể cả chunked và form không JavaScript; dùng cùng helper boundedBody, không chờ vô hạn trước lúc fetch API.

## M8 bổ sung

ProductResponse có brand/original_name và gallery images có quyền ở detail; listing giữ primary. GET products hỗ trợ available=true. real_demo chỉ nguồn/ảnh approved nhưng offer demo có nhãn rõ, không gọi là merchant-verified. GET manage/products trả read_only=true; mọi thay đổi qua form ở profile này trả409 thông báo hỗ trợ, không để UI giả tạo/duyệt ảnh. Các chức năng fixture demo_seed giữ riêng.
