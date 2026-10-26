"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { mutate, type Account } from "@/lib/commerce";
import {
  readCart,
  writeCart,
  setCartAccount,
  type CartLine,
} from "@/components/guest-cart";
import { credentialsSchema } from "@/lib/validation";
export function AuthForm({
  register = false,
  next,
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
          const account = await mutate<Account>(
            `/auth/${register ? "register" : "login"}`,
            checked.data,
          );
          const remote = await api<{
            items: {
              product_id: string;
              product_size_id: number;
              quantity: number;
            }[];
          }>("/cart");
          const merged = new Map<string, CartLine>();
          for (const line of [
            ...remote.items.map((i) => ({
              id: i.product_id,
              product_size_id: i.product_size_id,
              quantity: i.quantity,
            })),
            ...readCart(),
          ]) {
            const lineKey = `${line.id}-${line.product_size_id ?? "legacy"}`;
            const old = merged.get(lineKey);
            merged.set(lineKey, {
              ...line,
              quantity: Math.max(old?.quantity ?? 0, line.quantity),
            });
          }
          const lines = [...merged.values()].slice(0, 50);
          // An old guest cart may still need a size choice; keep it without blocking sign-in.
          if (lines.every((line) => line.product_size_id)) {
            await mutate(
              "/cart",
              {
                items: lines.map((r) => ({
                  product_id: r.id,
                  product_size_id: r.product_size_id,
                  quantity: r.quantity,
                })),
              },
              "PUT",
            );
          }
          setCartAccount(false);
          writeCart(lines);
          setCartAccount(true);
          const destination =
            next ??
            (account.roles.includes("admin") ? "/manage" : "/account/orders");
          router.push(
            destination.startsWith("/") &&
              !destination.startsWith("//") &&
              !destination.includes("\\")
              ? destination
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
