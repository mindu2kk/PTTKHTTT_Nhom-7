"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { money, type Category } from "@/lib/api";
import { mutate } from "@/lib/commerce";
import { ImportCatalog } from "@/components/import-catalog";
type Row = {
  id: string;
  name: string;
  category_id: string;
  status: string;
  review: string;
  price_vnd: number;
  seller_id: string;
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
export function ManageProducts({
  data,
  categories,
  admin,
  images,
}: {
  data: Managed;
  categories: Category[];
  admin: boolean;
  images: { id: string; url: string; alt: string }[];
}) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  async function action(path: string, body?: unknown, method = "POST") {
    setBusy(true);
    setMessage("");
    try {
      await mutate(path, body, method);
      setMessage("Đã lưu thay đổi.");
      router.refresh();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (data.read_only)
    return (
      <section>
        <p className="demo-note">
          Danh mục ảnh thật được cập nhật qua đợt nhập có kiểm duyệt. Tạo, sửa
          và duyệt bằng biểu mẫu chưa được hỗ trợ ở chế độ này.
        </p>
        <h2>Các bản ghi gần cập nhật</h2>
        <div className="managed-list">
          {data.items.map((row) => (
            <article className="order-card" key={row.id}>
              <h3>{row.name}</h3>
              <p>
                {row.status === "published"
                  ? "Đã xuất bản"
                  : row.status === "draft"
                    ? "Bản nháp"
                    : "Đã lưu trữ"}{" "}
                · {money(row.price_vnd)} (đặt thử)
              </p>
            </article>
          ))}
        </div>
      </section>
    );
  return (
    <>
      <p>
        Danh mục mô phỏng. Người bán tạo bản nháp; quản trị viên duyệt nguồn và
        xuất bản. Giá/tồn kho được đọc lại khi đặt hàng.
      </p>
      {message && <p role="status">{message}</p>}
      <details className="manage-create">
        <summary>Tạo sản phẩm mô phỏng</summary>
        <form
          className="account-form"
          onSubmit={async (e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            await action("/manage/products", {
              name: f.get("name"),
              description: f.get("description"),
              category_id: f.get("category"),
              image_id: f.get("image"),
              price_vnd: Number(f.get("price")),
              stock: Number(f.get("stock")),
              color: f.get("color"),
              material: f.get("material"),
              size: f.get("size"),
              original_data_confirmed: f.get("rights") === "on",
            });
          }}
        >
          <label>
            Tên sản phẩm
            <input name="name" required minLength={3} maxLength={250} />
          </label>
          <label>
            Mô tả
            <textarea
              name="description"
              required
              minLength={10}
              maxLength={3000}
            />
          </label>
          <label>
            Danh mục
            <select name="category">
              {categories
                .filter(
                  (c) => !categories.some((child) => child.parent_id === c.id),
                )
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name_vi}
                  </option>
                ))}
            </select>
          </label>
          <label>
            Ảnh minh họa đã duyệt
            <select name="image" required>
              {images.map((image) => (
                <option key={image.id} value={image.id}>
                  {image.alt}
                </option>
              ))}
            </select>
          </label>
          <p>
            Thư viện chỉ gồm ảnh gốc đã được duyệt quyền sử dụng. Không nhận ảnh
            từ đường dẫn bên ngoài.
          </p>
          <label>
            Giá (₫)
            <input name="price" type="number" min={1} max={1e12} required />
          </label>
          <label>
            Tồn kho
            <input name="stock" type="number" min={0} max={1000000} required />
          </label>
          <label>
            Màu
            <input name="color" maxLength={40} required />
          </label>
          <label>
            Chất liệu
            <input name="material" maxLength={100} required />
          </label>
          <label>
            Kích cỡ
            <input name="size" maxLength={30} required defaultValue="M" />
          </label>
          <label>
            <input name="rights" type="checkbox" required /> Tôi tạo và có quyền
            dùng dữ liệu mô phỏng này theo CC0.
          </label>
          <Button disabled={busy}>Lưu bản nháp</Button>
        </form>
      </details>
      {admin && <ImportCatalog />}
      <div className="managed-list">
        {data.items.map((row) => (
          <article className="order-card" key={row.id}>
            <h2>{row.name}</h2>
            <p>
              {row.id} ·{" "}
              {row.status === "published"
                ? "Đã xuất bản"
                : row.status === "archived"
                  ? "Đã lưu trữ"
                  : "Bản nháp"}{" "}
              · {row.review === "verified" ? "Đã duyệt" : "Chờ duyệt"}
            </p>
            <strong>{money(row.price_vnd)}</strong>
            <form
              className="offer-form"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                void action(
                  `/manage/products/${row.id}`,
                  {
                    price_vnd: Number(f.get("price")),
                    stock: Number(f.get("stock")),
                  },
                  "PATCH",
                );
              }}
            >
              <label>
                Giá mới (₫)
                <input
                  name="price"
                  type="number"
                  min={1}
                  max={1e12}
                  defaultValue={row.price_vnd}
                  required
                />
              </label>
              <label>
                Tổng tồn kho mới
                <input
                  name="stock"
                  type="number"
                  min={0}
                  max={1000000}
                  required
                />
              </label>
              <Button disabled={busy} variant="outline">
                Cập nhật
              </Button>
            </form>
            <div className="media-actions">
              {admin && row.status !== "published" && (
                <Button
                  disabled={busy}
                  onClick={() => action(`/manage/products/${row.id}/publish`)}
                >
                  Duyệt và xuất bản
                </Button>
              )}
              <Button
                disabled={busy}
                variant="outline"
                onClick={() => action(`/manage/products/${row.id}/archive`)}
              >
                Lưu trữ
              </Button>
            </div>
          </article>
        ))}
      </div>
      {admin && (
        <section>
          <h2>Đợt nhập và kiểm duyệt</h2>
          {data.batches.map((b) => (
            <p key={b.id}>
              {b.id} · {b.status} · {JSON.stringify(b.counts)} ·{" "}
              {b.errors.length} lỗi
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
        </section>
      )}
    </>
  );
}
