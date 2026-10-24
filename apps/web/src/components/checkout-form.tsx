"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { money, type Product } from "@/lib/api";
import { mutate, type Order } from "@/lib/commerce";
import { readCart, writeCart } from "@/components/guest-cart";
import { addressSchema } from "@/lib/validation";
export function CheckoutForm({ products }: { products: Product[] }) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [opened, setOpened] = useState(false);
  const key = useRef("");
  const payloadRef = useRef("");
  const router = useRouter();
  if (!opened)
    return <Button onClick={() => setOpened(true)}>Đặt đơn mô phỏng</Button>;
  return (
    <form
      className="account-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError("");
        const data = new FormData(e.currentTarget);
        const body = {
          items: readCart().map((line) => ({
            product_id: line.id,
            quantity: line.quantity,
            expected_price_vnd:
              products.find((p) => p.id === line.id)?.price_vnd || 0,
          })),
          address: {
            recipient: data.get("recipient"),
            phone: data.get("phone"),
            address_line: data.get("address"),
          },
          method: data.get("method"),
        };
        const serialized = JSON.stringify(body);
        if (payloadRef.current !== serialized) {
          key.current = crypto.randomUUID();
          payloadRef.current = serialized;
        }
        try {
          const checked = addressSchema.safeParse(body.address);
          if (!checked.success)
            throw new Error(checked.error.issues[0].message);
          body.address = checked.data;
          const order = await mutate<Order>(
            "/checkout",
            body,
            "POST",
            key.current,
          );
          writeCart([]);
          router.push(`/account/orders/${order.code}`);
          router.refresh();
        } catch (e) {
          setError((e as Error).message);
        } finally {
          setBusy(false);
        }
      }}
    >
      <h3>Thông tin nhận hàng mô phỏng</h3>
      <p>
        Đăng nhập trước khi đặt đơn. Không nhập địa chỉ nhạy cảm vào bản demo.
      </p>
      <Link href="/auth/login?next=/cart">Đăng nhập / đăng ký</Link>
      <label>
        Người nhận
        <input
          name="recipient"
          required
          minLength={2}
          maxLength={100}
          autoComplete="name"
        />
      </label>
      <label>
        Số điện thoại
        <input
          name="phone"
          type="tel"
          required
          pattern="\+?[0-9 ]{9,15}"
          autoComplete="tel"
        />
      </label>
      <label>
        Địa chỉ
        <input
          name="address"
          required
          minLength={8}
          maxLength={300}
          autoComplete="street-address"
        />
      </label>
      <label>
        Phương thức
        <select name="method">
          <option value="cod">COD mô phỏng</option>
          <option value="mock">Thanh toán mô phỏng</option>
        </select>
      </label>
      <p>
        Phí giao hàng demo: {money(0)}. Giá và tồn kho được kiểm tra lại khi xác
        nhận.
      </p>
      {error && <p role="alert">{error}</p>}
      <Button disabled={busy}>
        {busy ? "Đang tạo đơn…" : "Xác nhận đặt đơn mô phỏng"}
      </Button>
    </form>
  );
}
