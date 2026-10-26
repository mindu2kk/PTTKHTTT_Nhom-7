"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, money, Product } from "@/lib/api";
import {
  readCart,
  writeCart,
  useCart,
  sameLine,
  type CartLine,
} from "@/components/guest-cart";
import { CheckoutForm } from "@/components/checkout-form";
import { ProductPhoto } from "@/components/product-photo";
export function CartView() {
  const cart = useCart();
  const key = [...new Set(cart.map((p) => p.id))].join(",");
  const [products, setProducts] = useState<Product[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const failed = () =>
      setError(
        "Chưa đồng bộ được giỏ với tài khoản. Hãy tải lại trang và kiểm tra trước khi đặt đơn.",
      );
    window.addEventListener("hm-cart-sync-error", failed);
    return () => window.removeEventListener("hm-cart-sync-error", failed);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    Promise.all(
      key
        .split(",")
        .filter(Boolean)
        .map((id) =>
          api<Product>(`/products/${id}`, { signal: controller.signal }),
        ),
    )
      .then(setProducts)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [key]);
  const total = cart.reduce(
    (n, line) =>
      n +
      (products.find((p) => p.id === line.id)?.price_vnd || 0) * line.quantity,
    0,
  );
  function quantity(line: CartLine, value: number) {
    if (value < 1 || value > 99) return;
    const p = products.find((p) => p.id === line.id);
    const size = p?.sizes.find((s) => s.id === line.product_size_id);
    if (
      !p ||
      !size ||
      value > Math.min(Number(size.available_quantity), p.available_quantity)
    ) {
      setError("Số lượng vượt quá tồn kho hiện tại.");
      return;
    }
    writeCart(
      readCart().map((p) =>
        sameLine(p, line) ? { ...p, quantity: value } : p,
      ),
    );
  }
  if (loading) return <p role="status">Đang kiểm tra giỏ hàng…</p>;
  return (
    <>
      {error && (
        <p role="alert" className="error-note">
          {error}
        </p>
      )}
      {cart.length ? (
        <div className="cart-layout">
          <div>
            {cart.map((line) => {
              const product = products.find((p) => p.id === line.id);
              return (
                <article
                  key={`${line.id}-${line.product_size_id ?? "legacy"}`}
                  className="cart-line"
                >
                  {product && (
                    <ProductPhoto
                      src={product.image_url}
                      alt={product.image_alt}
                    />
                  )}
                  <div>
                    <h2>
                      <Link
                        href={
                          product ? `/products/${product.slug}` : "/products"
                        }
                      >
                        {product?.name_vi || "Sản phẩm hiện không khả dụng"}
                      </Link>
                    </h2>
                    <p>
                      {product?.color} · Size{" "}
                      {product?.sizes.find((s) => s.id === line.product_size_id)
                        ?.size || "Chưa chọn"}
                    </p>
                    {product && (
                      <label>
                        Size
                        <select
                          aria-label={`Size ${product.name_vi}`}
                          value={line.product_size_id ?? ""}
                          onChange={(e) => {
                            const id = Number(e.target.value);
                            const current = readCart();
                            if (
                              current.some(
                                (r) =>
                                  !sameLine(r, line) &&
                                  r.id === line.id &&
                                  r.product_size_id === id,
                              )
                            ) {
                              setError(
                                "Size này đã có trong giỏ. Hãy sửa số lượng ở dòng tương ứng.",
                              );
                              return;
                            }
                            writeCart(
                              current.map((r) =>
                                sameLine(r, line)
                                  ? { ...r, product_size_id: id, quantity: 1 }
                                  : r,
                              ),
                            );
                          }}
                        >
                          <option value="" disabled>
                            Chọn size
                          </option>
                          {product.sizes.map((s) => (
                            <option
                              key={s.id}
                              value={s.id}
                              disabled={Number(s.available_quantity) === 0}
                            >
                              {s.size}
                              {Number(s.available_quantity) === 0
                                ? " — Hết hàng"
                                : ""}
                            </option>
                          ))}
                        </select>
                      </label>
                    )}
                    <strong>{money(product?.price_vnd || 0)}</strong>
                    <p className="fine-print">
                      Giá đặt thử · Không có thanh toán thật
                    </p>
                    <div className="quantity-control">
                      <button
                        aria-label={`Giảm số lượng ${product?.name_vi}`}
                        onClick={() => quantity(line, line.quantity - 1)}
                      >
                        −
                      </button>
                      <output aria-label="Số lượng">{line.quantity}</output>
                      <button
                        aria-label={`Tăng số lượng ${product?.name_vi}`}
                        onClick={() => quantity(line, line.quantity + 1)}
                      >
                        +
                      </button>
                      <button
                        onClick={() =>
                          writeCart(
                            readCart().filter((p) => !sameLine(p, line)),
                          )
                        }
                      >
                        Xóa
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
          <aside className="order-summary">
            <h2>Đơn hàng của bạn</h2>
            <div>
              <span>Tạm tính</span>
              <strong>{money(total)}</strong>
            </div>
            <p>
              Đơn mô phỏng, chưa gồm phí giao hàng. Không có khoản thanh toán
              thật.
            </p>
            <CheckoutForm products={products} />
            <Link href="/products">Tiếp tục khám phá</Link>
          </aside>
        </div>
      ) : (
        <div className="empty-state">
          <h2>Giỏ hàng đang trống</h2>
          <p>Khám phá danh mục và chọn sản phẩm phù hợp.</p>
          <Link href="/products">Xem sản phẩm</Link>
        </div>
      )}
    </>
  );
}
