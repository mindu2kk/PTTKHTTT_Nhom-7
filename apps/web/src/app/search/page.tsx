import Link from "next/link";
import type { components } from "@/lib/schema";
import { ApiError, serverApi } from "@/lib/server-api";
import { money, type Category } from "@/lib/api";
import { SearchBar } from "@/components/search-bar";
import { ProductCard } from "@/components/product-card";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { OrderCard } from "@/components/order-card";
type Result =
  | components["schemas"]["SearchResponse"]
  | components["schemas"]["OrderSearchResponse"];
type Constraint = components["schemas"]["ConstraintResponse"];
const labels: Record<string, string> = {
  category: "Danh mục",
  color: "Màu",
  material: "Chất liệu",
  brand: "Thương hiệu",
  gender: "Giới tính",
  size: "Cỡ",
  price_min: "Giá từ",
  price_max: "Giá đến",
  season: "Mùa",
  style: "Phong cách",
  price_target: "Khoảng giá ưu tiên",
};
export default async function Search({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const first = (key: string) => {
    const value = params[key];
    return Array.isArray(value) ? value[0] : value;
  };
  const q = first("q") || "";
  const query = new URLSearchParams();
  for (const key of [
    "q",
    "modality",
    "category",
    "price_min",
    "price_max",
    "color",
    "material",
    "brand",
    "gender",
    "page",
    "sort",
  ])
    if (first(key)) query.set(key, first(key)!);
  if (params.allow_relax)
    for (const value of [params.allow_relax].flat())
      query.append("allow_relax", value);
  if (!q)
    return (
      <div className="wrap section-block">
        <h1>Tìm kiếm sản phẩm</h1>
        <SearchBar compact />
        <p>Nhập mô tả sản phẩm, chẳng hạn “áo len nam màu đen dưới 500k”.</p>
      </div>
    );
  let result: Result;
  let categories: Category[];
  try {
    [result, categories] = await Promise.all([
      serverApi<Result>(`/search/text?${query}`),
      serverApi<Category[]>("/categories"),
    ]);
  } catch (error) {
    if (error instanceof ApiError && error.status === 401)
      return (
        <div className="wrap section-block">
          <SearchBar initial={q} compact />
          <h1>Tra cứu đơn hàng</h1>
          <p>Đăng nhập để xem đơn hàng thuộc tài khoản của bạn.</p>
          <Link
            href={`/auth/login?next=${encodeURIComponent(`/search?q=${q}`)}`}
          >
            Đăng nhập
          </Link>
        </div>
      );
    if (error instanceof ApiError && [404, 422].includes(error.status))
      return (
        <div className="wrap section-block">
          <SearchBar initial={q} compact />
          <h1>Tra cứu đơn hàng</h1>
          <p>
            Không tìm thấy đơn hàng của bạn. Kiểm tra mã đơn và tài khoản đang
            đăng nhập.
          </p>
          <Link href="/account/orders">Đơn hàng của tôi</Link>
        </div>
      );
    throw error;
  }
  if (result.search_type === "order")
    return (
      <div className="wrap section-block">
        <SearchBar initial={q} compact />
        <h1>Kết quả tra cứu đơn hàng</h1>
        <OrderCard order={result.order} detail />
      </div>
    );
  const value = (c: Constraint) =>
    c.key === "category"
      ? String(c.value)
          .split("|")
          .map((id) => categories.find((cat) => cat.id === id)?.name_vi || id)
          .join(" / ")
      : c.key.startsWith("price")
        ? `${c.operator === "lt" ? "Dưới " : c.operator === "gt" ? "Trên " : ""}${money(Number(c.value))}`
        : String(c.value);
  const pageLink = (page: number) => {
    const next = new URLSearchParams(query);
    next.set("page", String(page));
    return `/search?${next}`;
  };
  const expand = new URLSearchParams(query);
  expand.set("allow_relax", "color");
  expand.delete("page");
  const canExpand =
    result.total < 3 &&
    result.query.hard_filters.some(
      (c) => c.key === "color" && c.origin === "explicit_text",
    );
  return (
    <div className="wrap section-block">
      <SearchBar initial={q} compact />
      <div className="section-heading">
        <div>
          <h1>Kết quả cho “{q}”</h1>
          <p>
            {result.total} sản phẩm ·{" "}
            {result.query.modality === "voice"
              ? "Giọng nói — bản ghi đã chỉnh sửa"
              : "Văn bản"}{" "}
            · giá đặt thử mô phỏng
          </p>
        </div>
      </div>
      <p>
        <Link href={`/assistant?q=${encodeURIComponent(q)}`}>
          Thử tìm theo mô tả hình dáng và so sánh sản phẩm
        </Link>
      </p>
      <div className="interpreted-filters">
        <h2>Điều kiện tìm kiếm</h2>
        <div className="active-filters">
          {result.query.hard_filters.map((c) => (
            <Badge
              variant="secondary"
              key={c.key}
              title={
                c.origin === "ui_selected"
                  ? "Bạn đã chọn trên bộ lọc"
                  : c.origin === "inferred"
                    ? "Được suy đoán từ mô tả"
                    : "Được nhận từ câu tìm kiếm"
              }
            >
              {labels[c.key] || c.key}: {value(c)}
            </Badge>
          ))}
          {result.query.soft_preferences.map((c) => (
            <Badge variant="outline" key={c.key}>
              Ưu tiên {value(c)}
            </Badge>
          ))}
          {result.query.relaxed_filters.map((c) => (
            <Badge variant="outline" key={c.key}>
              {labels[c.key]}: {value(c)} — đã nới
            </Badge>
          ))}
        </div>
      </div>
      {result.notices.map((notice, i) => (
        <Alert key={i}>
          <AlertTitle>Đã mở rộng kết quả</AlertTitle>
          <AlertDescription>
            {notice
              .replace("color", "màu")
              .replace("material", "chất liệu")
              .replace("gender", "giới tính")}
          </AlertDescription>
        </Alert>
      ))}
      {canExpand && (
        <Alert>
          <AlertTitle>Có ít sản phẩm phù hợp</AlertTitle>
          <AlertDescription>
            Giữ nguyên danh mục và giá. Bạn có thể cho phép chuyển màu thành ưu
            tiên để xem thêm sản phẩm.
            <Link className="text-link" href={`/search?${expand}`}>
              Cho phép mở rộng màu
            </Link>
          </AlertDescription>
        </Alert>
      )}
      <details className="search-refine">
        <summary>Điều chỉnh bộ lọc</summary>
        <form action="/search" method="get" className="refine-form">
          <input type="hidden" name="q" value={q} />
          {first("modality") && (
            <input type="hidden" name="modality" value={first("modality")} />
          )}
          <label>
            Danh mục
            <select name="category" defaultValue={first("category") || ""}>
              <option value="">Theo câu tìm kiếm</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {"— ".repeat(c.level)}
                  {c.name_vi}
                </option>
              ))}
            </select>
          </label>
          <label>
            Giá từ (₫)
            <input
              name="price_min"
              type="number"
              min="0"
              defaultValue={first("price_min")}
            />
          </label>
          <label>
            Giá đến (₫)
            <input
              name="price_max"
              type="number"
              min="0"
              defaultValue={first("price_max")}
            />
          </label>
          <label>
            Màu
            <input
              name="color"
              defaultValue={first("color")}
              placeholder="Ví dụ: đen"
            />
          </label>
          <label>
            Sắp xếp
            <select name="sort" defaultValue={first("sort") || "relevance"}>
              <option value="relevance">Phù hợp nhất</option>
              <option value="price_asc">Giá tăng dần</option>
              <option value="price_desc">Giá giảm dần</option>
            </select>
          </label>
          <Button type="submit">Áp dụng</Button>
        </form>
      </details>
      {result.items.length ? (
        <div className="product-grid">
          {result.items.map((row, i) => (
            <ProductCard
              key={row.product.id}
              product={row.product}
              eager={i < 4}
            />
          ))}
        </div>
      ) : (
        <div className="empty-state">
          <h2>Chưa có sản phẩm phù hợp</h2>
          <p>
            Thử mô tả ngắn hơn, kiểm tra danh mục hoặc điều chỉnh bộ lọc. Những
            điều kiện bạn chọn vẫn được giữ nguyên.
          </p>
          <Link href="/products">Khám phá danh mục</Link>
        </div>
      )}
      <nav className="pagination" aria-label="Phân trang kết quả">
        {result.page > 1 && (
          <Link href={pageLink(result.page - 1)}>Trang trước</Link>
        )}
        <span>
          Trang {result.page} /{" "}
          {Math.max(1, Math.ceil(result.total / result.page_size))}
        </span>
        {result.page * result.page_size < result.total && (
          <Link href={pageLink(result.page + 1)}>Trang sau</Link>
        )}
      </nav>
      <p className="fine-print">
        {result.engine}. Kết quả dựa trên dữ liệu danh mục đã xuất bản.
      </p>
    </div>
  );
}
