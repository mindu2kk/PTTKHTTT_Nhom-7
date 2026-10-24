import Link from "next/link";
import { serverApi } from "@/lib/server-api";
import type { Category, ProductPage } from "@/lib/api";
import { ProductCard } from "@/components/product-card";
import { Button } from "@/components/ui/button";
import { FilterPanel } from "@/components/filter-panel";
import { Suspense } from "react";
import { CatalogSkeleton } from "@/components/catalog-skeleton";
async function ProductResults({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const filters = await searchParams;
  const query = new URLSearchParams();
  for (const key of [
    "category",
    "price_min",
    "price_max",
    "color",
    "gender",
    "material",
    "brand",
    "size",
    "sort",
    "page",
    "available",
  ])
    if (filters[key]) query.set(key, filters[key]!);
  const [page, categories, facets] = await Promise.all([
    serverApi<ProductPage>(`/products?${query}`),
    serverApi<Category[]>("/categories"),
    serverApi<Record<string, string[]>>("/facets"),
  ]);
  const link = (n: number) => {
    const p = new URLSearchParams(query);
    p.set("page", String(n));
    return `/products?${p}`;
  };
  return (
    <div className="wrap section-block">
      <div className="section-heading">
        <div>
          <h1>Sản phẩm</h1>
          <p>{page.total} sản phẩm · Giá và đơn hàng đặt thử</p>
        </div>
      </div>
      <div className="catalog-layout">
        <FilterPanel>
          <section className="filters">
            <h2>Bộ lọc sản phẩm</h2>
            <form method="get" action="/products">
              <label htmlFor="category">Danh mục</label>
              <select
                id="category"
                name="category"
                defaultValue={filters.category || ""}
              >
                <option value="">Tất cả danh mục</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>
                    {"— ".repeat(c.level)}
                    {c.name_vi}
                  </option>
                ))}
              </select>
              <label htmlFor="min">Giá từ (₫)</label>
              <input
                id="min"
                name="price_min"
                type="number"
                min="0"
                defaultValue={filters.price_min}
              />
              <label htmlFor="max">Giá đến (₫)</label>
              <input
                id="max"
                name="price_max"
                type="number"
                min="0"
                defaultValue={filters.price_max}
              />
              <label htmlFor="color">Màu</label>
              <select
                id="color"
                name="color"
                defaultValue={filters.color || ""}
              >
                <option value="">Tất cả màu</option>
                {facets.color.map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
              <label htmlFor="gender">Giới tính</label>
              <select
                id="gender"
                name="gender"
                defaultValue={filters.gender || ""}
              >
                <option value="">Tất cả</option>
                {facets.gender.map((g) => (
                  <option key={g}>{g}</option>
                ))}
              </select>
              {[
                ["material", "Chất liệu"],
                ["brand", "Thương hiệu"],
                ["size", "Kích cỡ"],
              ].map(
                ([key, label]) =>
                  facets[key]?.length > 0 && (
                    <div key={key}>
                      <label htmlFor={key}>{label}</label>
                      <select
                        id={key}
                        name={key}
                        defaultValue={filters[key] || ""}
                      >
                        <option value="">Tất cả</option>
                        {facets[key].map((v) => (
                          <option key={v}>{v}</option>
                        ))}
                      </select>
                    </div>
                  ),
              )}
              <label htmlFor="sort">Sắp xếp</label>
              <select
                id="sort"
                name="sort"
                defaultValue={filters.sort || "newest"}
              >
                <option value="newest">Mới nhất</option>
                <option value="price_asc">Giá tăng dần</option>
                <option value="price_desc">Giá giảm dần</option>
              </select>
              <Button type="submit">Áp dụng bộ lọc</Button>
              <label className="check-filter">
                <input
                  type="checkbox"
                  name="available"
                  value="true"
                  defaultChecked={filters.available === "true"}
                />
                Có thể đặt thử
              </label>
              <Link href="/products">Xóa bộ lọc</Link>
            </form>
          </section>
        </FilterPanel>
        <div>
          <div className="catalog-toolbar">
            <span>Sắp xếp theo</span>
            {[
              ["newest", "Mới thêm"],
              ["price_asc", "Giá tăng dần"],
              ["price_desc", "Giá giảm dần"],
            ].map(([value, label]) => {
              const next = new URLSearchParams(query);
              next.set("sort", value);
              next.delete("page");
              return (
                <Link
                  key={value}
                  href={`/products?${next}`}
                  aria-current={
                    (filters.sort || "newest") === value ? "page" : undefined
                  }
                >
                  {label}
                </Link>
              );
            })}
            <span>{page.total} kết quả</span>
          </div>
          <div className="active-filters">
            {Object.entries(filters)
              .filter(([k, v]) => v && k !== "page")
              .map(([k, v]) => (
                <span key={k}>
                  {k === "category"
                    ? categories.find((c) => c.id === v)?.name_vi || v
                    : v}
                </span>
              ))}
          </div>
          {page.items.length ? (
            <div className="product-grid catalog-grid">
              {page.items.map((p, i) => (
                <ProductCard key={p.id} product={p} eager={i < 3} />
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <h2>Chưa có sản phẩm phù hợp</h2>
              <p>Hãy thử khoảng giá rộng hơn hoặc chọn danh mục khác.</p>
              <Link href="/products">Xem tất cả sản phẩm</Link>
            </div>
          )}
          <nav className="pagination" aria-label="Phân trang">
            {page.page > 1 && (
              <Link href={link(page.page - 1)}>Trang trước</Link>
            )}
            <span>
              Trang {page.page} /{" "}
              {Math.max(1, Math.ceil(page.total / page.page_size))}
            </span>
            {page.page * page.page_size < page.total && (
              <Link href={link(page.page + 1)}>Trang sau</Link>
            )}
          </nav>
        </div>
      </div>
    </div>
  );
}

export default function Products({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  return (
    <Suspense fallback={<CatalogSkeleton />}>
      <ProductResults searchParams={searchParams} />
    </Suspense>
  );
}
