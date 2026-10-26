"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Product } from "@/lib/api";
import { readCart, writeCart, sameLine } from "@/components/guest-cart";
export function AddToCart({ product }: { product: Product }) {
  const [message, setMessage] = useState("");
  const router = useRouter();
  const [sizeId, setSizeId] = useState(
    product.sizes.length === 1 ? String(product.sizes[0].id) : "",
  );
  const selected = product.sizes.find((size) => String(size.id) === sizeId);
  const available = Math.min(
    Number(selected?.available_quantity ?? 0),
    product.available_quantity,
  );
  return (
    <form
      method="post"
      action="/cart/add"
      className="purchase-form"
      onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const qty = Number(form.get("quantity"));
        if (!selected) {
          setMessage("Hãy chọn size trước khi thêm vào giỏ.");
          return;
        }
        const line = {
          id: product.id,
          product_size_id: Number(selected.id),
          quantity: qty,
        };
        const cart = readCart();
        const old = cart.find((p) => sameLine(p, line));
        if ((!old && cart.length >= 50) || qty + (old?.quantity || 0) > 99) {
          setMessage(
            "Giỏ tối đa 50 sản phẩm khác nhau, mỗi sản phẩm tối đa 99.",
          );
          return;
        }
        if (
          !Number.isInteger(qty) ||
          qty < 1 ||
          qty + (old?.quantity || 0) > available
        ) {
          setMessage("Số lượng vượt quá tồn kho hiện tại.");
          return;
        }
        try {
          writeCart([
            ...cart.filter((p) => !sameLine(p, line)),
            { ...line, quantity: qty + (old?.quantity || 0) },
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
      <label htmlFor="product-size">Kích cỡ</label>
      <select
        id="product-size"
        name="product_size_id"
        value={sizeId}
        required
        onChange={(e) => {
          setSizeId(e.target.value);
          setMessage("");
        }}
      >
        <option value="" disabled>
          Chọn size
        </option>
        {product.sizes.map((size) => (
          <option
            key={size.id}
            value={size.id}
            disabled={Number(size.available_quantity) === 0}
          >
            {size.size === "F" ? "F — Không phân size" : size.size}
            {Number(size.available_quantity) === 0 ? " — Hết hàng" : ""}
          </option>
        ))}
      </select>
      {selected && (
        <p role="status">
          Còn {available} sản phẩm cho size {selected.size}.
        </p>
      )}
      <label htmlFor="quantity">Số lượng</label>
      <input
        id="quantity"
        name="quantity"
        type="number"
        min={1}
        max={Math.max(1, Math.min(99, selected ? available : product.available_quantity))}
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
