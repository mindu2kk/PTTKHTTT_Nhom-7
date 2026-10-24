"""Build the new handoff only from its saved evidence; preserve M7/M8 reports."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/evidence/marketplace-ai"


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8-sig"))


def main():
    runtime, browser, regression = (
        read("runtime.json"),
        read("browser.json"),
        read("regression/browser.json"),
    )
    catalog, media = read("catalog-state.json"), read("media-checks.json")
    cold = read("first-real-text-encoder.json")
    tests = re.search(
        r"(\d+) passed in ([\d.]+)s", (OUT / "pytest.txt").read_text(encoding="utf8")
    )
    assert tests and browser["result"] == regression["result"] == "passed"
    assert (
        catalog["local_only"]
        and catalog["approved_photos"] == catalog["compatible_vectors"]
    )
    rows = "\n".join(
        f"| {r['q']} | {', '.join(r['top5_categories'])} | {r['precision_at_5']:.2f} |"
        for r in runtime["results"]
    )
    report = f"""# Marketplace và AI — bàn giao 2026-10-23

## Đã triển khai

- Tham khảo cấu trúc trang chủ [Shopee](https://shopee.vn/) bằng Browser: utility bar/tìm kiếm/giỏ, banner chính và ô kề, lối tắt, danh mục, bộ sưu tập. Sau đọc cây nội dung gặp CAPTCHA; không vượt chặn, không nhận đã xem đầy đủ listing/PDP hay backend nội bộ Shopee. FE/BE ở đây là mã riêng của HoodooMart. Kế hoạch và token tại [MARKETPLACE_AI_PLAN](MARKETPLACE_AI_PLAN.md).
- Home gọn hơn, banner dùng sản phẩm thật, ảnh danh mục, Sheet danh mục có keyboard/focus, đường dẫn công cụ AI, tài khoản/role/đăng xuất theo phiên thật. Không tạo khuyến mại, đánh giá hoặc doanh số.
- `/assistant`: mô tả hình dáng → text tower của **OpenCLIP ViT-B/32 đang có** → vector512D cùng revision với gallery → cosine trong danh mục/giá/màu đã lọc. Không tải model mới, không API trả phí. Mapping Việt→khái niệm tiếng Anh hữu hạn; không LLM/chatbot tổng quát hay machine translation tự do.
- Giữ danh mục/ngân sách khi sửa câu; phân trang dùng snapshot điều kiện đã tìm. So sánh tối đa3 sản phẩm, truy vấn lại public catalog, hiển thị thuộc tính/nguồn/giá đặt thử, chỉ nói giá thấp nhất trong các lựa chọn. Không tự kết luận độ bền/chất lượng/hiệu năng hay tạo đơn.
- Image/Whisper tiếp tục suy luận thật, voice correction có lối sang tìm hình dáng. Không lưu hội thoại, raw ảnh/audio hoặc bản chép lời vào catalog.

Catalog hiện tại: **{catalog["public_products"]} sản phẩm public, {catalog["approved_photos"]} ảnh được duyệt, {catalog["compatible_vectors"]} vector tương thích**, profile `{catalog["profile"]}`, LOCAL_ONLY=true. Không nhập thêm nguồn hoặc sửa ảnh/giá/kho/dữ liệu người dùng. Giấy phép ABO CC-BY-4.0 và attribution M8 giữ nguyên. Schema không đổi, head0005.

## Kiểm thử đã chạy

- Baseline:151 passed/72.02s (`../artifacts/marketplace-ai-baseline.txt`); DB test riêng do conftest bắt buộc hậu tố `_test`.
- Final: **{tests[1]} passed/{tests[2]}s**, JUnit và log trong evidence/marketplace-ai. Bao gồm layer boundaries, rights, uploads, CSRF/IDOR/order/stock, mô tả không hiểu/order intent, bounded input, prefilter, so sánh/ẩn record và regression homograph/xếp hạng.
- Ruff/format, mypy39 source files, ESLint, TypeScript, Alembic check và build Docker đạt; logs tại evidence/marketplace-ai, build `artifacts/marketplace-ai-verified-build.log`, web cuối `artifacts/marketplace-ai-web-verified-build.log`.
- Chrome mới: **{len(browser["results"])} nhóm/{browser["elapsed_seconds"]}s**, home5 viewport360/390/768/1280/1440, Sheet/focus, AI thật, budget/context/page, compare, unknown recovery, keyword, mobile voice correction và đăng nhập/đăng xuất thật. Screenshot kiểm trực tiếp trong cùng thư mục. Voice correction được gõ, không gọi là ASR/TC2.
- Regression Chrome M8 chạy lại và ghi tách: **{len(regression["results"])} nhóm đạt**, gallery/zoom/cart/checkout/ownership/stock/cancel/voice/image/management cùng responsive. Không ghi đè evidence M8 cũ.
- ASR qua BFF trên1 VIVOS human clip {media["sample_id"]}, {media["duration_seconds"]}s: HTTP {media["asr_http_ms"]}ms, WER={media["wer"]:.4f}; chỉ kiểm adapter hoạt động, không phải TC2 hoặc benchmark chất lượng tiếng Việt đại diện. Corrupt image/audio422; Origin giả403; JSON text worker sai/field dư422, body>2048B413. Không tái phân phối audio/transcript private.

## Số đo mới

Lượt mô tả đầu thực tế API: {cold["http_ms"]}ms, có tải model từ đĩa; không gọi là cache OS lạnh. Model dùng chung cho ảnh/mô tả, semaphore một tác vụ CPU. Không cam kết mọi lần dưới1s.

{runtime["query_count"]} câu tự soạn trong từ vựng hữu hạn; {runtime["uncached_count"]} lượt không cache và {runtime["cached_count"]} cache-equivalent tách riêng. Qua BFF HTTP trên catalog318: **warm uncached p50={runtime["warm_uncached_p50_ms"]}ms, p95={runtime["warm_uncached_p95_ms"]}ms**. Top1 khớp nhóm nguồn={runtime["top1_category_match_rate"]:.2f}; mean P@5={runtime["mean_precision_at_5"]:.2f}. Đây là proxy theo category nguồn, không human judgments, không phép đo hiểu mọi mô tả tiếng Việt. Các câu cố ý không trùng tên category; bộ từ vựng vẫn hữu hạn. Giữ kết quả kém trong bảng, không bỏ mẫu.

| Câu | Nhóm của top5 | P@5 |
|---|---|---:|
{rows}

Latency/quality M8 và benchmark3k mô phỏng M7 là lịch sử riêng, không dùng làm kết quả mới. Không đo field INP, peak RAM hay quy mô thật1000/3000 trong đợt này.

## Lỗi đã gặp và sửa

Từ “đồ” sau bỏ dấu bị hiểu thành màu đỏ. Đã loại homograph khi còn dấu và thêm kiểm tra vẫn giữ đỏ trong “đồ màu đỏ”; bản sửa đầu làm mất cả đỏ, regression bắt lỗi trước bàn giao. Xếp hạng mô tả trước đó gộp cosine gần nhau thành cùng band rồi ưu tiên ID: dùng độ chính xác cao hơn riêng nhánh mô tả. Không đổi band ảnh M8. `runtime-before-homograph-fix.json` giữ nguyên kết quả lỗi; nhãn qrels tên category cũng đã sửa đúng catalog, nên không dùng chênh lệch trước/sau làm thước đo cải tiến model.

Hai lỗi harness Chrome: alert trùng route announcer của Next, và chờ utility bar đang ẩn ở mobile. Đã scope alert và kiểm logout mobile qua trang tài khoản, desktop qua utility bar. Bổ sung nhãn tài khoản cho icon mobile. ESLint chạy root không có config; chạy lại đúng apps/web đạt. Log chi tiết cục bộ giữ trong artifacts, không nhận các lượt lỗi là đạt.

## Tệp thay đổi chính xác

- Backend: `apps/api/app/domain/media.py`; `application/search.py`, `application/query_parser.py`, `application/shopping_assistant.py` (mới); `infrastructure/media.py`; `core/dependencies.py`; `api/v1/assistant.py` (mới); `app/main.py`; `apps/inference/main.py`; `apps/api/tests/test_shopping_assistant.py` (mới).
- FE: `apps/web/src/app/page.tsx`, `layout.tsx`, `marketplace-ai.css` (mới), `assistant/page.tsx` (mới), `search/page.tsx`, `search/image/page.tsx`, `search/voice/page.tsx`; components `site-header.tsx`, `voice-search.tsx`, `category-menu.tsx`, `marketplace-banner.tsx`, `ai-navigation.tsx`, `shopping-assistant.tsx` (4 tệp sau mới); `src/lib/schema.ts`, `docs/openapi.json` sinh lại.
- Tools: `benchmarks/scripts/marketplace_ai_runtime.py`, `marketplace_ai_browser.py`, `marketplace_ai_regression.py`, `scripts/report_marketplace_ai.py` (mới).
- Docs: README, PROGRESS, IMPLEMENTATION_PLAN, API_CONTRACTS, ARCHITECTURE; hai tài liệu MARKETPLACE_AI; evidence/marketplace-ai mới. Không có Git trong workspace khi kiểm, nên đây là danh sách theo tệp sửa, không `git diff`. Báo cáo nghiệm thu M7/M8 giữ nguyên.

## Chạy và kiểm lại

Mở [HoodooMart](http://localhost:3000), [Trợ lý](http://localhost:3000/assistant), [API](http://localhost:8000/docs). Models/dataset đã có trên máy; khởi động không tải ngầm.

```powershell
docker compose --env-file .env -f infra/docker-compose.yml up -d --build --wait
.\\.venv\\Scripts\\python.exe -m pytest apps/api/tests -q --junitxml=docs/evidence/marketplace-ai/pytest.xml
.\\.venv\\Scripts\\python.exe benchmarks/scripts/marketplace_ai_runtime.py
.\\.venv\\Scripts\\python.exe benchmarks/scripts/marketplace_ai_browser.py
.\\.venv\\Scripts\\python.exe benchmarks/scripts/marketplace_ai_regression.py
```

TEST_DATABASE_URL phải là DB riêng hoodoomart_test. Chạy tuần tự sau build. Muốn đo mới tránh cache prompt, restart API rồi chờ health; worker có thể giữ model warm. Không dùng lượt cache-hit làm uncached latency. Tái tạo catalog/model theo README và RUNBOOK, phải có đồng ý trước weights mới.

## Giới hạn và việc còn lại

TC2 nguyên câu vẫn chờ file âm thanh thật của người dùng; chưa được gửi. Whisper base còn yếu; browser on-device thử nghiệm, không dùng cloud thay thế. Mô tả chỉ hỗ trợ từ vựng đã ghi; thuộc tính nguồn thiếu vẫn thiếu, ảnh có thể gồm nhiều vật thể làm lệch ranking. Không có LLM tư vấn kiến thức mở hoặc nhận diện chính xác SKU chỉ từ ảnh. Giá/kho/đơn thử mô phỏng, không thanh toán/giao hàng thật. Chưa mở rộng catalog thật1000/3000 hoặc đầy đủ34 leaf. Không gọi đây là bản production Shopee.

![Trang chủ hoàn thiện](evidence/marketplace-ai/home-preview.png)
"""
    (ROOT / "docs/MARKETPLACE_AI_REPORT.md").write_text(report, encoding="utf8")
    print("Marketplace/AI report generated from final evidence")


if __name__ == "__main__":
    main()
