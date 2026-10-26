import Link from "next/link";
import { money } from "@/lib/api";
import { type Order, statusLabel } from "@/lib/commerce";
export function OrderCard({
  order,
  detail = false,
}: {
  order: Order;
  detail?: boolean;
}) {
  return (
    <article className="order-card">
      <div className="section-heading">
        <h2>
          <Link href={`/account/orders/${encodeURIComponent(order.code)}`}>
            Đơn {order.code}
          </Link>
        </h2>
        <strong>{statusLabel[order.status] || order.status}</strong>
      </div>
      <p>
        Dữ liệu mô phỏng ·{" "}
        {new Date(order.created_at).toLocaleDateString("vi-VN")}
      </p>
      {order.items.map((line) => (
        <div
          className="order-item"
          key={`${line.product_id}-${line.product_size_id ?? "legacy"}`}
        >
          <span>
            {line.name}
            {line.size
              ? ` · Size ${line.size}`
              : " · Chưa ghi nhận size"} × {line.quantity}
          </span>
          <strong>{money(line.unit_price_vnd * line.quantity)}</strong>
        </div>
      ))}
      <p className="order-total">
        Tổng cộng <strong>{money(order.total_vnd)}</strong>
      </p>
      {detail && (
        <>
          <p>
            Phương thức:{" "}
            {order.payment_method === "mock"
              ? "Thanh toán mô phỏng"
              : "COD mô phỏng"}
            . Không có khoản thu thật.
          </p>
          {order.address.recipient && (
            <p>
              {order.address.recipient} · {order.address.phone}
              <br />
              {order.address.address_line}
            </p>
          )}
        </>
      )}
    </article>
  );
}
