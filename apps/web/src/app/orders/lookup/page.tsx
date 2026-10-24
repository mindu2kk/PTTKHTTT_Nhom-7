import Link from "next/link";
import { ApiError, serverApi } from "@/lib/server-api";
import type { Order } from "@/lib/commerce";
import { OrderCard } from "@/components/order-card";
import { Button } from "@/components/ui/button";
export default async function Lookup({
  searchParams,
}: {
  searchParams: Promise<{ code?: string }>;
}) {
  const { code } = await searchParams;
  let order: Order | undefined;
  let message = "";
  let login = false;
  if (code) {
    try {
      order = await serverApi<Order>(
        `/orders/${encodeURIComponent(code.trim().toUpperCase())}`,
      );
    } catch (e) {
      if (e instanceof ApiError && [401, 404].includes(e.status)) {
        login = e.status === 401;
        message = login
          ? "Đăng nhập để tra cứu đơn thuộc tài khoản của bạn."
          : "Không tìm thấy đơn hàng của bạn.";
      } else throw e;
    }
  }
  return (
    <div className="wrap section-block narrow">
      <h1>Tra cứu đơn hàng</h1>
      <form action="/orders/lookup" className="account-form">
        <label>
          Mã đơn hàng
          <input name="code" required maxLength={40} defaultValue={code} />
        </label>
        <Button>Tra cứu</Button>
      </form>
      {message && <p role="status">{message}</p>}
      {login && (
        <Link
          href={`/auth/login?next=${encodeURIComponent(`/orders/lookup?code=${code}`)}`}
        >
          Đăng nhập
        </Link>
      )}
      {order && <OrderCard order={order} detail />}
    </div>
  );
}
