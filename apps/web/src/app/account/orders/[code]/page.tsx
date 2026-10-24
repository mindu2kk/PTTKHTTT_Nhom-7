import { ApiError, serverApi } from "@/lib/server-api";
import type { Order } from "@/lib/commerce";
import { OrderCard } from "@/components/order-card";
import { CancelOrder } from "@/components/account-forms";
import Link from "next/link";
import { notFound } from "next/navigation";
export default async function OrderPage({
  params,
}: {
  params: Promise<{ code: string }>;
}) {
  const { code } = await params;
  let order: Order;
  try {
    order = await serverApi<Order>(`/orders/${encodeURIComponent(code)}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    if (e instanceof ApiError && e.status === 401)
      return (
        <div className="wrap section-block">
          <h1>Chi tiết đơn hàng</h1>
          <Link
            href={`/auth/login?next=${encodeURIComponent(`/account/orders/${code}`)}`}
          >
            Đăng nhập để xem đơn hàng của bạn
          </Link>
        </div>
      );
    throw e;
  }
  return (
    <div className="wrap section-block narrow">
      <h1>Chi tiết đơn hàng</h1>
      <OrderCard order={order} detail />
      {["CONFIRMED", "PACKING"].includes(order.status) && (
        <CancelOrder code={code} />
      )}
      <Link href="/account/orders">Tất cả đơn hàng</Link>
    </div>
  );
}
