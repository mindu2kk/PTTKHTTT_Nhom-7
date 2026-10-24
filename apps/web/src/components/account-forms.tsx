"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { mutate, type Account } from "@/lib/commerce";
import { readCart, writeCart, setCartAccount } from "@/components/guest-cart";
import { credentialsSchema } from "@/lib/validation";
export function AuthForm({
  register = false,
  next = "/account/orders",
}: {
  register?: boolean;
  next?: string;
}) {
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  return (
    <form
      className="account-form"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        setError("");
        const data = new FormData(e.currentTarget);
        try {
          const checked = credentialsSchema.safeParse({
            email: data.get("email"),
            password: data.get("password"),
          });
          if (!checked.success)
            throw new Error(checked.error.issues[0].message);
          await mutate<Account>(
            `/auth/${register ? "register" : "login"}`,
            checked.data,
          );
          const remote = await api<{
            items: { product_id: string; quantity: number }[];
          }>("/cart");
          const merged = new Map(
            remote.items.map((i) => [i.product_id, i.quantity]),
          );
          for (const row of readCart())
            merged.set(row.id, Math.max(merged.get(row.id) || 0, row.quantity));
          const lines = [...merged]
            .slice(0, 50)
            .map(([id, quantity]) => ({ id, quantity }));
          await mutate(
            "/cart",
            {
              items: lines.map((r) => ({
                product_id: r.id,
                quantity: r.quantity,
              })),
            },
            "PUT",
          );
          writeCart(lines);
          router.push(
            next.startsWith("/") &&
              !next.startsWith("//") &&
              !next.includes("\\")
              ? next
              : "/account/orders",
          );
          router.refresh();
        } catch (e) {
          setError(e instanceof Error ? e.message : "Chưa đăng nhập được.");
        } finally {
          setBusy(false);
        }
      }}
    >
      <label>
        Email
        <input
          name="email"
          type="email"
          autoComplete="email"
          required
          maxLength={250}
        />
      </label>
      <label>
        Mật khẩu
        <input
          name="password"
          type="password"
          required
          minLength={10}
          maxLength={128}
          autoComplete={register ? "new-password" : "current-password"}
        />
      </label>
      <p>
        Mật khẩu từ 10 đến 128 ký tự. Dùng thông tin mô phỏng khi trải nghiệm
        đặt hàng.
      </p>
      {error && <p role="alert">{error}</p>}
      <Button disabled={busy}>
        {busy ? "Đang xử lý…" : register ? "Tạo tài khoản" : "Đăng nhập"}
      </Button>
      <Link href={`/auth/${register ? "login" : "register"}`}>
        {register ? "Đã có tài khoản? Đăng nhập" : "Chưa có tài khoản? Đăng ký"}
      </Link>
    </form>
  );
}
export function AccountTools({ account }: { account: Account }) {
  const [enabled, setEnabled] = useState(account.history_opt_in);
  const [notice, setNotice] = useState("");
  const router = useRouter();
  return (
    <section className="account-tools">
      <p>{account.email}</p>
      <Link href="/account/history">Lịch sử tìm kiếm</Link>
      {account.roles.some((r) => r === "admin" || r === "seller") && (
        <Link href="/manage">Quản lý sản phẩm</Link>
      )}
      <label>
        <input
          type="checkbox"
          checked={enabled}
          onChange={async (e) => {
            const value = e.target.checked;
            setEnabled(value);
            try {
              await mutate("/history", { enabled: value }, "PATCH");
              setEnabled(value);
              setNotice(
                value
                  ? "Đã bật. Lưu tối đa 100 câu trong 7 ngày; không lưu ảnh và âm thanh."
                  : "Đã tắt và xóa lịch sử.",
              );
            } catch (e) {
              setEnabled(!value);
              setNotice((e as Error).message);
            }
          }}
        />{" "}
        Cho phép lưu lịch sử tìm kiếm
      </label>
      <Button
        variant="outline"
        onClick={async () => {
          try {
            await mutate("/history", undefined, "DELETE");
            setNotice("Đã xóa lịch sử.");
            router.refresh();
          } catch (e) {
            setNotice((e as Error).message);
          }
        }}
      >
        Xóa lịch sử
      </Button>
      <Button
        variant="outline"
        onClick={async () => {
          try {
            await mutate("/auth/logout");
            setCartAccount(false);
            writeCart([]);
            router.push("/auth/login");
            router.refresh();
          } catch (e) {
            setNotice((e as Error).message);
          }
        }}
      >
        Đăng xuất
      </Button>
      {notice && <p role="status">{notice}</p>}
    </section>
  );
}
export function CancelOrder({ code }: { code: string }) {
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  return (
    <div>
      <Button
        variant="outline"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await mutate(`/orders/${code}`, { status: "CANCELLED" }, "PATCH");
            router.refresh();
          } catch (e) {
            setMessage((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        Hủy đơn mô phỏng
      </Button>
      {message && <p role="alert">{message}</p>}
    </div>
  );
}
