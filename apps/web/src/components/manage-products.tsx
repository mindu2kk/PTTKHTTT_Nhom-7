"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { money, type Category } from "@/lib/api";
import { mutate } from "@/lib/commerce";
import { ImportCatalog } from "@/components/import-catalog";
import { ProductPhoto } from "@/components/product-photo";

const SIZES = ["S", "M", "L", "XL", "XXL", "F"];
type Row = {
  id: string;
  name: string;
  description: string;
  category_id: string;
  status: string;
  review: string;
  price_vnd: number;
  seller_id: string;
  color: string;
  material: string;
  brand: string;
  image_id: string;
  image_url: string;
  image_urls: string[];
  updated_at: string;
  sizes: { size: string; stock: number; reserved: number }[];
};
export type Managed = {
  read_only?: boolean;
  items: Row[];
  batches: {
    id: string;
    status: string;
    counts: Record<string, number>;
    errors: unknown[];
  }[];
};
function ProductFields({
  row,
  categories,
}: {
  row?: Row;
  categories: Category[];
}) {
  const [selected, setSelected] = useState(
    row?.sizes.map((s) => s.size) ?? ["M"],
  );
  const initialUrls =
    row?.image_urls ?? (row?.image_url ? [row.image_url] : []);
  const [imageText, setImageText] = useState(initialUrls.join("\n"));
  const imageUrls = imageText
    .split(/\r?\n/)
    .map((url) => url.trim())
    .filter(Boolean);
  const imagesChanged =
    JSON.stringify(imageUrls) !== JSON.stringify(initialUrls);
  const leaves = categories.filter(
    (c) => !categories.some((child) => child.parent_id === c.id),
  );
  return (
    <>
      <div className="admin-product-fields">
        <label>
          Tên sản phẩm
          <input
            name="name"
            required
            minLength={3}
            maxLength={250}
            defaultValue={row?.name}
          />
        </label>
        <label>
          Danh mục
          <select
            name="category"
            required
            defaultValue={
              leaves.some((c) => c.id === row?.category_id)
                ? row?.category_id
                : ""
            }
          >
            <option value="" disabled>
              Chọn danh mục
            </option>
            {leaves.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name_vi}
              </option>
            ))}
          </select>
        </label>
        <label>
          Giá (₫)
          <input
            name="price"
            type="number"
            step={1}
            min={1}
            max={1e12}
            required
            defaultValue={row?.price_vnd}
          />
        </label>
        <label>
          Màu sắc
          <input
            name="color"
            maxLength={40}
            required
            defaultValue={row?.color}
          />
        </label>
        <label>
          Chất liệu
          <input
            name="material"
            maxLength={100}
            required
            defaultValue={row?.material}
          />
        </label>
        <label>
          Thương hiệu
          <input name="brand" maxLength={80} defaultValue={row?.brand} />
        </label>
      </div>
      <label>
        Mô tả
        <textarea
          name="description"
          required
          minLength={10}
          maxLength={3000}
          defaultValue={row?.description}
        />
      </label>
      <label>
        URL ảnh sản phẩm (mỗi dòng một URL)
        <textarea
          name="image_urls"
          required
          rows={4}
          maxLength={20480}
          value={imageText}
          onChange={(e) => setImageText(e.target.value)}
          placeholder={
            "https://i.postimg.cc/.../anh-1.jpg\nhttps://i.postimg.cc/.../anh-2.jpg"
          }
        />
      </label>
      <p className="fine-print">
        Ảnh đầu tiên là ảnh bìa. Tối đa 10 ảnh trực tiếp từ i.postimg.cc
        (Postimages), JPG/PNG/WebP, mỗi ảnh tối đa 5 MB.
      </p>
      <div className="admin-gallery-preview">
        {imageUrls
          .filter(
            (url) =>
              /^https:\/\/i\.postimg\.cc\//.test(url) ||
              url.startsWith("/media/catalog/"),
          )
          .slice(0, 10)
          .map((url, index) => (
            <figure className="admin-image-preview" key={`${url}-${index}`}>
              <ProductPhoto src={url} alt={`Xem trước ảnh ${index + 1}`} />
              <figcaption>
                {index === 0 ? "Ảnh bìa" : `Ảnh ${index + 1}`}
              </figcaption>
            </figure>
          ))}
      </div>
      {row && imagesChanged && (
        <label className="admin-checkbox">
          <input name="image-rights" type="checkbox" required />
          Tôi có quyền sử dụng các ảnh này trên website.
        </label>
      )}
      <fieldset className="admin-sizes">
        <legend>Size và tồn kho</legend>
        <p>
          Chọn F cho phụ kiện không phân size. Tồn kho bao gồm số lượng đang giữ
          cho đơn hàng.
        </p>
        <div className="admin-size-grid">
          {SIZES.map((size) => {
            const old = row?.sizes.find((s) => s.size === size);
            return (
              <div className="admin-size-row" key={size}>
                <label>
                  <input
                    type="checkbox"
                    name="sizes"
                    value={size}
                    checked={selected.includes(size)}
                    onChange={(e) =>
                      setSelected(
                        e.target.checked
                          ? [...selected, size]
                          : selected.filter((s) => s !== size),
                      )
                    }
                  />
                  {size}
                </label>
                <input
                  aria-label={`Tồn kho size ${size}`}
                  name={`stock-${size}`}
                  type="number"
                  step={1}
                  min={old?.reserved ?? 0}
                  max={1000000}
                  required={selected.includes(size)}
                  disabled={!selected.includes(size)}
                  defaultValue={old?.stock ?? 0}
                />
                <small>Đang giữ: {old?.reserved ?? 0}</small>
              </div>
            );
          })}
        </div>
      </fieldset>
    </>
  );
}
function formProduct(form: FormData) {
  const sizes = form.getAll("sizes").map((size) => ({
    size: String(size),
    stock: Number(form.get(`stock-${size}`)),
  }));
  if (!sizes.length) throw new Error("Hãy chọn ít nhất một size hoặc F.");
  return {
    name: String(form.get("name") ?? "").trim(),
    description: String(form.get("description") ?? "").trim(),
    category_id: form.get("category"),
    image_urls: String(form.get("image_urls") ?? "")
      .split(/\r?\n/)
      .map((url) => url.trim())
      .filter(Boolean),
    image_rights_confirmed:
      form.get("image-rights") === "on" || form.get("rights") === "on",
    price_vnd: Number(form.get("price")),
    color: String(form.get("color") ?? "").trim(),
    material: String(form.get("material") ?? "").trim(),
    brand: String(form.get("brand") ?? "").trim(),
    sizes,
    stock: sizes.reduce((n, s) => n + s.stock, 0),
  };
}
export function ManageProducts({
  data,
  categories,
  admin,
}: {
  data: Managed;
  categories: Category[];
  admin: boolean;
}) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [createKey, setCreateKey] = useState(0);
  const router = useRouter();
  async function action(path: string, body?: unknown, method = "POST") {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await mutate(path, body, method);
      setMessage("Đã lưu thay đổi.");
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const rows = data.items.filter((row) =>
    `${row.name} ${row.id}`
      .toLocaleLowerCase("vi-VN")
      .includes(search.toLocaleLowerCase("vi-VN")),
  );
  if (data.read_only)
    return (
      <section>
        <p>Chỉ quản trị viên được thêm và sửa sản phẩm trong danh mục này.</p>
        {data.items.map((row) => (
          <p key={row.id}>
            {row.name} — {money(row.price_vnd)}
          </p>
        ))}
      </section>
    );
  return (
    <>
      <p>Thêm mặt hàng, chỉnh sửa thông tin và quản lý tồn kho theo size.</p>
      {message && <p role="status">{message}</p>}
      {error && (
        <p role="alert" className="error-note">
          {error}
        </p>
      )}
      <details className="manage-create">
        <summary>Thêm mặt hàng mới</summary>
        <form
          key={createKey}
          className="account-form admin-product-form"
          onSubmit={async (e) => {
            e.preventDefault();
            setBusy(true);
            setMessage("");
            setError("");
            try {
              const f = new FormData(e.currentTarget);
              const body = formProduct(f);
              const result = await mutate<{ id: string }>("/manage/products", {
                ...body,
                size: body.sizes.map((s) => s.size).join(", "),
                original_data_confirmed: f.get("rights") === "on",
              });
              if (admin && f.get("publish") === "on")
                await mutate(`/manage/products/${result.id}/publish`);
              setMessage(
                f.get("publish") === "on"
                  ? "Đã thêm và xuất bản mặt hàng."
                  : "Đã lưu bản nháp. Bạn có thể xuất bản trong danh sách bên dưới.",
              );
              setCreateKey((key) => key + 1);
              router.refresh();
            } catch (e) {
              setError((e as Error).message);
            } finally {
              setBusy(false);
            }
          }}
        >
          <fieldset disabled={busy} className="admin-form-fields">
            <ProductFields categories={categories} />
            <label className="admin-checkbox">
              <input name="rights" type="checkbox" required />
              Tôi tạo và có quyền sử dụng thông tin sản phẩm theo CC0, đồng thời
              có quyền dùng ảnh này trên website.
            </label>
            {admin && (
              <label className="admin-checkbox">
                <input name="publish" type="checkbox" />
                Xuất bản sau khi thêm
              </label>
            )}
            <Button disabled={busy}>Thêm mặt hàng</Button>
          </fieldset>
        </form>
      </details>
      <label className="admin-search">
        Tìm mặt hàng
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Tên hoặc mã sản phẩm"
        />
      </label>
      <p>{rows.length} mặt hàng</p>
      <div className="managed-list">
        {rows.map((row) => (
          <article className="order-card" key={`${row.id}-${row.updated_at}`}>
            <div className="admin-product-summary">
              {row.image_url && (
                <div className="admin-image-preview">
                  <ProductPhoto src={row.image_url} alt={row.name} />
                </div>
              )}
              <div>
                <h2>{row.name}</h2>
                <p>Mã sản phẩm: {row.id.replace(/^rhodi-/, "hoodoo-")}</p>
                <p>
                  {row.status === "published"
                    ? "Đang hiển thị"
                    : row.status === "archived"
                      ? "Đã ẩn"
                      : "Bản nháp"}{" "}
                  · {money(row.price_vnd)}
                </p>
                <p>
                  {row.sizes
                    .map((s) => `${s.size}: ${s.stock - s.reserved} còn hàng`)
                    .join(" · ")}
                </p>
              </div>
            </div>
            <details>
              <summary>Chỉnh sửa sản phẩm</summary>
              <form
                className="account-form admin-product-form"
                onSubmit={(e) => {
                  e.preventDefault();
                  try {
                    const f = new FormData(e.currentTarget);
                    void action(
                      `/manage/products/${row.id}`,
                      admin
                        ? formProduct(f)
                        : {
                            price_vnd: Number(f.get("price")),
                            stock: Number(f.get("stock")),
                          },
                      "PATCH",
                    );
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                <fieldset disabled={busy} className="admin-form-fields">
                  {admin ? (
                    <ProductFields row={row} categories={categories} />
                  ) : (
                    <>
                      <label>
                        Giá (₫)
                        <input
                          name="price"
                          type="number"
                          min={1}
                          max={1e12}
                          required
                          defaultValue={row.price_vnd}
                        />
                      </label>
                      <label>
                        Tồn kho
                        <input
                          name="stock"
                          type="number"
                          min={0}
                          max={1000000}
                          required
                          defaultValue={row.sizes.reduce(
                            (n, s) => n + s.stock,
                            0,
                          )}
                        />
                      </label>
                    </>
                  )}
                  <Button disabled={busy}>Lưu thay đổi</Button>
                </fieldset>
              </form>
            </details>
            <div className="media-actions">
              {admin && row.status !== "published" && (
                <Button
                  disabled={busy}
                  onClick={() =>
                    void action(`/manage/products/${row.id}/publish`)
                  }
                >
                  Xuất bản
                </Button>
              )}
              {row.status !== "archived" && (
                <Button
                  disabled={busy}
                  variant="outline"
                  onClick={() =>
                    void action(`/manage/products/${row.id}/archive`)
                  }
                >
                  Ẩn sản phẩm
                </Button>
              )}
            </div>
          </article>
        ))}
      </div>
      {admin && (
        <details className="manage-create">
          <summary>Nhập danh sách và quản lý đơn hàng</summary>
          <ImportCatalog />
          <h2>Đợt nhập gần đây</h2>
          {data.batches.map((b) => (
            <p key={b.id}>
              {b.id} · {b.status} · {b.errors.length} lỗi
            </p>
          ))}
          <form
            className="offer-form"
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              void action(
                `/orders/${encodeURIComponent(String(f.get("code")))}`,
                { status: f.get("status") },
                "PATCH",
              );
            }}
          >
            <label>
              Mã đơn
              <input name="code" required />
            </label>
            <label>
              Trạng thái tiếp theo
              <select name="status">
                <option value="PACKING">Đang chuẩn bị</option>
                <option value="SHIPPED">Đang giao</option>
                <option value="DELIVERED">Đã giao</option>
                <option value="CANCELLED">Hủy</option>
              </select>
            </label>
            <Button disabled={busy}>Cập nhật đơn mô phỏng</Button>
          </form>
        </details>
      )}
    </>
  );
}
