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
