"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Camera, X } from "lucide-react";
import { api, money, type Category } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/schema";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldGroup,
  FieldLabel,
  FieldDescription,
} from "@/components/ui/field";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { ProductCard } from "@/components/product-card";
import { Skeleton } from "@/components/ui/skeleton";
type Result = components["schemas"]["SearchResponse"];
export function ImageSearch({
  categories,
  initial = {},
}: {
  categories: Category[];
  initial?: Record<string, string | undefined>;
}) {
  const [file, setFile] = useState<File>();
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState<Result>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const form = useRef<HTMLFormElement>(null);
  const picker = useRef<HTMLInputElement>(null);
  const controller = useRef<AbortController | null>(null);
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );
  useEffect(() => () => controller.current?.abort(), []);
  function choose(selected?: File) {
    controller.current?.abort();
    setBusy(false);
    setFile(undefined);
    setPreview("");
    setError("");
    setResult(undefined);
    if (!selected) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(selected.type)) {
      setError(
        "Chỉ nhận JPEG, PNG hoặc WebP. Hãy đổi định dạng nếu ảnh là HEIC.",
      );
      return;
    }
    if (selected.size > 5 * 1024 * 1024) {
      setError("Ảnh tối đa 5 MB. Vui lòng chọn ảnh nhỏ hơn.");
      return;
    }
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
  }
  async function search(page = 1) {
    if (!file || !form.current) {
      setError("Hãy chọn một ảnh sản phẩm trước.");
      return;
    }
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setBusy(true);
    setError("");
    setResult(undefined);
    const data = new FormData(form.current);
    data.set("image", file);
    data.set("page", String(page));
    for (const [key, value] of [...data.entries()])
      if (value === "") data.delete(key);
    try {
      const response = await api<Result>("/search/image", {
        method: "POST",
        body: data,
        signal: abort.signal,
      });
      if (!abort.signal.aborted) {
        setResult(response);
        const query = new URLSearchParams();
        for (const key of ["category", "price_min", "price_max", "text"])
          if (data.get(key)) query.set(key, String(data.get(key)));
        query.set("page", String(page));
        history.replaceState(null, "", `/search/image?${query}`);
      }
    } catch (e) {
      if (!abort.signal.aborted)
        setError(
          e instanceof Error
            ? e.message
            : "Chưa tìm được ảnh. Vui lòng thử lại.",
        );
    } finally {
      if (!abort.signal.aborted) setBusy(false);
    }
  }
  return (
    <>
      <form
        ref={form}
        onSubmit={(e) => {
          e.preventDefault();
          void search();
        }}
        className="media-workbench"
      >
        <FieldGroup>
          <Field>
            <FieldLabel htmlFor="product-image">Ảnh sản phẩm</FieldLabel>
            <div
              className="upload-zone"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                choose(e.dataTransfer.files[0]);
              }}
            >
              <Camera aria-hidden="true" />
              <p>Kéo ảnh vào đây hoặc chọn tệp</p>
              <input
                ref={picker}
                className="sr-only"
                id="product-image"
                name="image"
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={(e) => choose(e.target.files?.[0])}
              />
              <Button
                type="button"
                variant="outline"
                onClick={() => picker.current?.click()}
              >
                Chọn ảnh sản phẩm
              </Button>
              {file && <p>{file.name}</p>}
              <FieldDescription>
                JPEG, PNG hoặc WebP · tối đa 5 MB. Ảnh chỉ được xử lý tạm thời,
                không lưu vào danh mục.
              </FieldDescription>
            </div>
          </Field>
          <Field>
            <FieldLabel htmlFor="image-text">
              Mô tả thêm (không bắt buộc)
            </FieldLabel>
            <input
              id="image-text"
              name="text"
              defaultValue={initial.text}
              maxLength={300}
              placeholder="Ví dụ: áo len nam dưới 500k"
            />
          </Field>
          <Field>
            <FieldLabel htmlFor="image-category">Danh mục</FieldLabel>
            <select
              id="image-category"
              name="category"
              defaultValue={initial.category || ""}
            >
              <option value="">Tất cả danh mục</option>
              {categories.map((c) => (
                <option value={c.id} key={c.id}>
                  {"— ".repeat(c.level)}
                  {c.name_vi}
                </option>
              ))}
            </select>
          </Field>
          <Field>
            <FieldLabel htmlFor="image-max">Giá tối đa (₫)</FieldLabel>
            <input
              id="image-max"
              name="price_max"
              type="number"
              min="0"
              defaultValue={initial.price_max}
            />
          </Field>
          <Button type="submit" disabled={busy || !file}>
            {busy ? "Đang so sánh ảnh…" : "Tìm sản phẩm tương tự"}
          </Button>
          {busy && (
            <p role="status" className="text-sm text-muted-foreground">
              Lần tìm đầu sau khi khởi động có thể mất gần một phút. Bạn có thể
              hủy xử lý và tìm bằng văn bản.
            </p>
          )}
          {busy && (
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
          )}
        </FieldGroup>
        {preview && (
          <figure className="upload-preview">
            <img src={preview} alt="Ảnh bạn vừa chọn để tìm sản phẩm" />
            <figcaption>Ảnh tìm kiếm của bạn</figcaption>
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                controller.current?.abort();
                setBusy(false);
                setFile(undefined);
                setPreview("");
                setResult(undefined);
              }}
            >
              <X data-icon="inline-start" />
              Xóa ảnh
            </Button>
          </figure>
        )}
      </form>
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Chưa tìm được sản phẩm từ ảnh</AlertTitle>
          <AlertDescription>
            {error}
            <Link href="/search">Chuyển sang tìm văn bản</Link>
          </AlertDescription>
        </Alert>
      )}
      {busy && (
        <div className="product-grid" role="status" aria-label="Đang xử lý ảnh">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="aspect-square" />
          ))}
        </div>
      )}
      {result && (
        <section className="section-block">
          <h2>{result.total} sản phẩm tương tự</h2>
          <div className="active-filters" aria-label="Điều kiện tìm ảnh">
            {result.query.hard_filters.map((c) => (
              <Badge variant="secondary" key={c.key}>
                {(
                  {
                    category: "Danh mục",
                    color: "Màu",
                    material: "Chất liệu",
                    gender: "Giới tính",
                    brand: "Thương hiệu",
                    price_min: "Giá từ",
                    price_max: "Giá đến",
                  } as Record<string, string>
                )[c.key] || c.key}
                :{" "}
                {c.key === "category"
                  ? String(c.value)
                      .split("|")
                      .map(
                        (v) =>
                          categories.find((cat) => cat.id === v)?.name_vi || v,
                      )
                      .join(" / ")
                  : c.key.startsWith("price")
                    ? money(Number(c.value))
                    : String(c.value)}
              </Badge>
            ))}
            {result.query.soft_preferences.map((c) => (
              <Badge variant="outline" key={c.key}>
                Ưu tiên {String(c.value)}
              </Badge>
            ))}
          </div>
          <p className="fine-print">
            Hình ảnh · {result.engine}. Độ giống không xác minh được thương
            hiệu, chất liệu hay giá từ ảnh.
          </p>
          {result.notices.map((n, i) => (
            <p key={i}>{n}</p>
          ))}
          {result.items.length ? (
            <div className="product-grid">
              {result.items.map((row) => (
                <ProductCard key={row.product.id} product={row.product} />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <h3>Chưa có ảnh phù hợp trong danh mục</h3>
              <p>Thử ảnh có sản phẩm rõ hơn hoặc điều chỉnh bộ lọc.</p>
            </div>
          )}
          <nav className="pagination" aria-label="Phân trang ảnh">
            {result.page > 1 && (
              <Button
                variant="outline"
                onClick={() => void search(result.page - 1)}
              >
                Trang trước
              </Button>
            )}
            <span>Trang {result.page}</span>
            {result.page * result.page_size < result.total && (
              <Button
                variant="outline"
                onClick={() => void search(result.page + 1)}
              >
                Trang sau
              </Button>
            )}
          </nav>
        </section>
      )}
    </>
  );
}
