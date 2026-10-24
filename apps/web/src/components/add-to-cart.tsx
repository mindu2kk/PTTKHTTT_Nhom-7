"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Product } from "@/lib/api";
import { readCart, writeCart } from "@/components/guest-cart";
export function AddToCart({ product }: { product: Product }) {
  const [message, setMessage] = useState("");
  const router = useRouter();
  return (
    <form
      method="post"
      action="/cart/add"
      className="purchase-form"
      onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const qty = Number(form.get("quantity"));
        const cart = readCart();
        const old = cart.find((p) => p.id === product.id);
        if ((!old && cart.length >= 50) || qty + (old?.quantity || 0) > 99) {
          setMessage(
            "Giỏ tối đa 50 sản phẩm khác nhau, mỗi sản phẩm tối đa 99.",
          );
          return;
        }
        if (
          !Number.isInteger(qty) ||
          qty < 1 ||
          qty + (old?.quantity || 0) > product.available_quantity
        ) {
          setMessage("Số lượng vượt quá tồn kho hiện tại.");
          return;
        }
        try {
          writeCart([
            ...cart.filter((p) => p.id !== product.id),
            { id: product.id, quantity: qty + (old?.quantity || 0) },
          ]);
        } catch {
          setMessage(
            "Chưa lưu được giỏ hàng trong trình duyệt. Hãy kiểm tra quyền lưu trữ.",
          );
          return;
        }
        setMessage("Đã thêm vào giỏ hàng.");
        if (
          (event.nativeEvent as SubmitEvent).submitter?.getAttribute(
            "value",
          ) === "buy-now"
        )
          router.push("/cart");
      }}
    >
      <input type="hidden" name="id" value={product.id} />
      <label htmlFor="variant">Phiên bản sản phẩm</label>
      <select id="variant" name="variant" defaultValue={product.size}>
        <option value={product.size}>
          {product.size} — {product.color}
        </option>
      </select>
      <label htmlFor="quantity">Số lượng</label>
      <input
        id="quantity"
        name="quantity"
        type="number"
        min={1}
        max={Math.min(99, product.available_quantity)}
        defaultValue={1}
        disabled={product.available_quantity === 0}
      />
      <Button type="submit" disabled={product.available_quantity === 0}>
        {product.available_quantity === 0
          ? "Sản phẩm đã hết hàng"
          : "Thêm vào giỏ hàng"}
      </Button>
      <Button
        type="submit"
        name="action"
        value="buy-now"
        variant="outline"
        disabled={product.available_quantity === 0}
      >
        Đặt thử ngay
      </Button>
      <p role="status" aria-live="polite">
        {message}
      </p>
    </form>
  );
}
