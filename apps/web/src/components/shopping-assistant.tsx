"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Sparkles, Scale, X } from "lucide-react";
import { api, money, type Category } from "@/lib/api";
import type { components } from "@/lib/schema";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductCard } from "@/components/product-card";
type Result = components["schemas"]["SearchResponse"];
type Comparison = components["schemas"]["CompareResponse"];
const EXAMPLES = [
  "Giày thể thao trắng",
  "Ghế bọc da màu nâu",
  "Đèn bàn tối giản",
  "Ốp lưng màu đen",
];
export function ShoppingAssistant({
  categories,
  initial,
}: {
  categories: Category[];
  initial: string;
}) {
  const [query, setQuery] = useState(initial);
  const [result, setResult] = useState<Result>();
  const [comparison, setComparison] = useState<Comparison>();
  const [selected, setSelected] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  const controller = useRef<AbortController | null>(null);
  const lastRequest = useRef<Record<string, string | number> | null>(null);
  useEffect(() => () => controller.current?.abort(), []);
  async function search(page = 1, previous = false) {
    if (!form.current) return;
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError("");
    setResult(undefined);
    setComparison(undefined);
    setSelected([]);
    const data = new FormData(form.current);
    let body: Record<string, string | number> = {
      q: query.trim(),
      page_size: 12,
    };
    for (const key of ["mode", "category", "price_max", "sort"]) {
      const value = String(data.get(key) || "");
      if (value) body[key] = key === "price_max" ? Number(value) : value;
    }
    if (previous && lastRequest.current) body = { ...lastRequest.current };
    body.page = page;
    lastRequest.current = { ...body };
    try {
      const response = await api<Result>("/search/describe", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: abort.signal,
      });
      if (!abort.signal.aborted) setResult(response);
    } catch (e) {
      if (!abort.signal.aborted)
        setError(
          e instanceof Error
            ? e.message
            : "Chưa tìm được sản phẩm. Hãy thử lại.",
        );
    } finally {
      if (!abort.signal.aborted) setBusy(false);
    }
  }
  async function compare() {
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError("");
    setComparison(undefined);
    try {
      const response = await api<Comparison>("/search/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ids: selected }),
        signal: abort.signal,
      });
      if (!abort.signal.aborted) setComparison(response);
    } catch (e) {
      if (!abort.signal.aborted)
        setError(
          e instanceof Error ? e.message : "Chưa so sánh được. Hãy thử lại.",
        );
    } finally {
      if (!abort.signal.aborted) setBusy(false);
    }
  }
  return (
    <>
      <div className="assistant-layout">
        <form
          ref={form}
          className="assistant-form"
          onSubmit={(e) => {
            e.preventDefault();
            void search();
          }}
        >
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="assistant-query">
                Bạn muốn tìm món gì?
              </FieldLabel>
              <textarea
                id="assistant-query"
                name="q"
                rows={3}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                minLength={1}
                maxLength={300}
                required
                placeholder="Ví dụ: ghế bọc da màu nâu dưới 2 triệu"
              />
              <FieldDescription>
                Hỗ trợ các loại như giày, sofa, ghế, đèn, thảm, ốp lưng và phụ
                kiện. Mô tả rõ loại sản phẩm để có kết quả sát hơn.
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="assistant-mode">Cách tìm</FieldLabel>
              <select name="mode" id="assistant-mode" defaultValue="visual">
                <option value="visual">AI so mô tả với ảnh</option>
                <option value="keyword">Tìm từ khóa trong dữ liệu</option>
              </select>
              <FieldDescription>
                AI dùng OpenCLIP có sẵn trên máy. Từ vựng Việt hữu hạn; không
                phải chatbot hiểu mọi yêu cầu.
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="assistant-category">
                Giữ trong danh mục
              </FieldLabel>
              <select name="category" id="assistant-category" defaultValue="">
                <option value="">Tất cả danh mục</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {"— ".repeat(c.level)}
                    {c.name_vi}
                  </option>
                ))}
              </select>
            </Field>
            <Field>
              <FieldLabel htmlFor="assistant-budget">
                Ngân sách tối đa (₫)
              </FieldLabel>
              <input
                name="price_max"
                id="assistant-budget"
                type="number"
                min={0}
                max={1e12}
                step={1}
                placeholder="Ví dụ: 1000000"
              />
              <FieldDescription>
                Danh mục và ngân sách được giữ khi bạn sửa câu tìm kiếm.
              </FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="assistant-sort">Sắp xếp</FieldLabel>
              <select name="sort" id="assistant-sort">
                <option value="relevance">Phù hợp trước</option>
                <option value="price_asc">Giá tăng dần</option>
                <option value="price_desc">Giá giảm dần</option>
              </select>
            </Field>
            <Button type="submit" disabled={busy || !query.trim()}>
              <Sparkles data-icon="inline-start" />
              {busy ? "Đang xử lý…" : "Tìm lựa chọn phù hợp"}
            </Button>
            {busy && (
              <>
                <p role="status">
                  Lần đầu cần tải mô hình từ đĩa. Bạn có thể hủy và dùng tìm từ
                  khóa.
                </p>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    controller.current?.abort();
                    setBusy(false);
                  }}
                >
                  Hủy xử lý
                </Button>
              </>
            )}
          </FieldGroup>
        </form>
        <section
          className="assistant-results"
          aria-label="Kết quả hỗ trợ chọn sản phẩm"
          aria-busy={busy}
        >
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Chưa hoàn tất yêu cầu</AlertTitle>
              <AlertDescription>
                {error}
                {error.includes("Đơn hàng") || error.includes("đơn của bạn") ? (
                  <Link href="/account/orders">Xem đơn hàng của tôi</Link>
                ) : null}
              </AlertDescription>
            </Alert>
          )}
          {!result && !busy && (
            <div className="assistant-empty">
              <Sparkles aria-hidden="true" />
              <h2>Bắt đầu từ một mô tả</h2>
              <p>
                Chọn gợi ý để điền câu, sau đó bấm tìm. Bạn luôn kiểm soát danh
                mục và ngân sách.
              </p>
              <div className="assistant-examples">
                {EXAMPLES.map((text) => (
                  <Button
                    variant="outline"
                    key={text}
                    type="button"
                    onClick={() => {
                      setQuery(text);
                      document.getElementById("assistant-query")?.focus();
                    }}
                  >
                    {text}
                  </Button>
                ))}
              </div>
              <p>
                Ảnh và thuộc tính có nguồn. Không tạo đánh giá, doanh số hay
                thông số còn thiếu.
              </p>
            </div>
          )}
          {busy && !result && (
            <div className="product-grid">
              {Array.from({ length: 6 }, (_, i) => (
                <Skeleton className="h-64" key={i} />
              ))}
            </div>
          )}
          {result && (
            <>
              <div className="section-heading">
                <div>
                  <h2>
                    {result.total
                      ? "Các lựa chọn dành cho bạn"
                      : "Chưa có lựa chọn khớp"}
                  </h2>
                  <p role="status">
                    {result.total} sản phẩm · đang hiển thị{" "}
                    {result.items.length} · trang {result.page}
                  </p>
                </div>
              </div>
              {!result.total && (
                <p>
                  Thử mô tả ngắn hơn, chọn danh mục khác hoặc tự thay ngân sách.
                  Điều kiện của bạn không bị tự nới.
                </p>
              )}
              <p className="assistant-engine">{result.engine}</p>
              <div className="product-grid assistant-product-grid">
                {result.items.map((row) => (
                  <div key={row.product.id}>
                    <ProductCard product={row.product} />
                    <label className="compare-choice">
                      <input
                        type="checkbox"
                        checked={selected.includes(row.product.id)}
                        disabled={
                          busy ||
                          (!selected.includes(row.product.id) &&
                            selected.length >= 3)
                        }
                        onChange={(e) => {
                          setComparison(undefined);
                          setSelected((old) =>
                            e.target.checked
                              ? [...old, row.product.id]
                              : old.filter((id) => id !== row.product.id),
                          );
                        }}
                      />
                      Chọn so sánh
                    </label>
                  </div>
                ))}
              </div>
              {result.total > result.page_size && (
                <nav
                  className="assistant-pagination"
                  aria-label="Trang kết quả trợ lý"
                >
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy || result.page <= 1}
                    onClick={() => void search(result.page - 1, true)}
                  >
                    Trang trước
                  </Button>
                  <span>
                    {result.page} / {Math.ceil(result.total / result.page_size)}
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={
                      busy || result.page * result.page_size >= result.total
                    }
                    onClick={() => void search(result.page + 1, true)}
                  >
                    Trang sau
                  </Button>
                </nav>
              )}
              {result.items.length > 0 && (
                <div className="compare-bar">
                  <span aria-live="polite">
                    Đã chọn {selected.length}/3 sản phẩm
                  </span>
                  <Button
                    type="button"
                    disabled={selected.length < 2 || busy}
                    onClick={() => void compare()}
                  >
                    <Scale data-icon="inline-start" />
                    So sánh lựa chọn
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    disabled={!selected.length || busy}
                    onClick={() => {
                      setSelected([]);
                      setComparison(undefined);
                    }}
                  >
                    <X data-icon="inline-start" />
                    Bỏ chọn
                  </Button>
                </div>
              )}
              <details className="assistant-method">
                <summary>Cách tìm và giới hạn</summary>
                <p>
                  {result.notices.join(" ") ||
                    "Tìm từ khóa và lọc trên dữ liệu công khai. Giá và hạn mức đặt thử mô phỏng."}
                </p>
                {result.media?.visual_prompt && (
                  <p>
                    Mô tả đưa vào bộ mã hóa:{" "}
                    {String(result.media.visual_prompt)}
                  </p>
                )}
                <p>
                  Điểm xếp hạng không phải xác suất đúng. Không dùng để kết luận
                  chất lượng, độ bền hoặc hiệu năng.
                </p>
              </details>
            </>
          )}
        </section>
      </div>
      {comparison && (
        <section
          className="comparison-section"
          aria-labelledby="comparison-title"
        >
          <h2 id="comparison-title">So sánh từ dữ liệu sản phẩm</h2>
          <p>{comparison.notice}</p>
          <div
            className="comparison-scroll"
            tabIndex={0}
            aria-label="Bảng so sánh có thể cuộn ngang"
          >
            <table>
              <thead>
                <tr>
                  <th scope="col">Thuộc tính</th>
                  {comparison.products.map((p) => (
                    <th scope="col" key={p.id}>
                      <Link href={`/products/${p.slug}`}>{p.name_vi}</Link>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {[
                  [
                    "Danh mục",
                    (p: Comparison["products"][number]) => p.category_name,
                  ],
                  [
                    "Giá đặt thử",
                    (p: Comparison["products"][number]) =>
                      money(p.price_vnd) +
                      (comparison.lowest_price_ids.includes(p.id)
                        ? " — thấp nhất trong lựa chọn"
                        : ""),
                  ],
                  [
                    "Thương hiệu",
                    (p: Comparison["products"][number]) =>
                      p.brand || "Chưa có thông tin",
                  ],
                  [
                    "Màu sắc",
                    (p: Comparison["products"][number]) =>
                      p.color || "Chưa có thông tin",
                  ],
                  [
                    "Chất liệu",
                    (p: Comparison["products"][number]) =>
                      p.material || "Chưa có thông tin",
                  ],
                  [
                    "Hạn mức đặt thử",
                    (p: Comparison["products"][number]) =>
                      String(p.available_quantity),
                  ],
                  ["Nguồn", (p: Comparison["products"][number]) => p.source_id],
                ].map(([label, format]) => (
                  <tr key={String(label)}>
                    <th scope="row">{String(label)}</th>
                    {comparison.products.map((p) => (
                      <td key={p.id}>
                        {typeof format === "function" ? format(p) : ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  );
}
