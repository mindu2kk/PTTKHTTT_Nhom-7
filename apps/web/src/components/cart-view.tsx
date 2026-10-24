"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, money, Product } from "@/lib/api";
import { readCart, writeCart, useCart } from "@/components/guest-cart";
import { CheckoutForm } from "@/components/checkout-form";
import { ProductPhoto } from "@/components/product-photo";
export function CartView() {
  const cart = useCart();
  const key = cart.map((p) => p.id).join(",");
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
  function quantity(id: string, value: number) {
    if (value < 1 || value > 99) return;
    const p = products.find((p) => p.id === id);
    if (!p || value > p.available_quantity) {
      setError("Số lượng vượt quá tồn kho hiện tại.");
      return;
    }
    writeCart(
      readCart().map((p) => (p.id === id ? { ...p, quantity: value } : p)),
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
                <article key={line.id} className="cart-line">
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
                      {product?.color} · {product?.size}
                    </p>
                    <strong>{money(product?.price_vnd || 0)}</strong>
                    <p className="fine-print">
                      Giá đặt thử · Không có thanh toán thật
                    </p>
                    <div className="quantity-control">
                      <button
                        aria-label={`Giảm số lượng ${product?.name_vi}`}
                        onClick={() => quantity(line.id, line.quantity - 1)}
                      >
                        −
                      </button>
                      <output aria-label="Số lượng">{line.quantity}</output>
                      <button
                        aria-label={`Tăng số lượng ${product?.name_vi}`}
                        onClick={() => quantity(line.id, line.quantity + 1)}
                      >
                        +
                      </button>
                      <button
                        onClick={() =>
                          writeCart(readCart().filter((p) => p.id !== line.id))
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
