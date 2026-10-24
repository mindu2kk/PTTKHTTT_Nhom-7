import Link from "next/link";
import { ApiError, serverApi } from "@/lib/server-api";
import type { Account, Order } from "@/lib/commerce";
import { OrderCard } from "@/components/order-card";
import { AccountTools } from "@/components/account-forms";
export default async function Orders() {
  let account: Account;
  let orders: Order[];
  try {
    [account, orders] = await Promise.all([
      serverApi<Account>("/auth/me"),
      serverApi<Order[]>("/orders"),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401)
      return (
        <div className="wrap section-block narrow">
          <h1>Đơn hàng của tôi</h1>
          <p>Đăng nhập để xem đơn hàng thuộc tài khoản của bạn.</p>
          <Link href="/auth/login">Đăng nhập</Link>
        </div>
      );
    throw e;
  }
  return (
    <div className="wrap section-block">
      <h1>Đơn hàng của tôi</h1>
      <AccountTools account={account} />
      <form action="/orders/lookup" className="order-lookup">
        <label>
          Tra cứu mã đơn
          <input
            name="code"
            required
            placeholder="Ví dụ: 20261005"
            maxLength={300}
          />
        </label>
        <button type="submit">Tra cứu</button>
      </form>
      {orders.length ? (
        orders.map((order) => <OrderCard key={order.code} order={order} />)
      ) : (
        <div className="empty-state">
          <h2>Bạn chưa có đơn hàng</h2>
          <Link href="/products">Khám phá sản phẩm</Link>
        </div>
      )}
    </div>
  );
}
