"use client";
import Link from "next/link";
import {
  ShoppingBag,
  UserRound,
  Headphones,
  Store,
  PackageCheck,
  Sparkles,
} from "lucide-react";
import { CategoryMenu } from "@/components/category-menu";
import { SearchBar } from "@/components/search-bar";
import type { Category } from "@/lib/api";
import { useCart, setCartAccount, writeCart } from "@/components/guest-cart";
import { CartSync } from "@/components/cart-sync";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { SearchToolButton } from "@/components/unified-search";
export function SiteHeader({
  categories,
  account,
}: {
  categories: Category[];
  account: { roles: string[] } | null;
}) {
  const cart = useCart();
  const router = useRouter();
  const [logoutError, setLogoutError] = useState("");
  const [loggingOut, setLoggingOut] = useState(false);
  async function logout() {
    setLoggingOut(true);
    setLogoutError("");
    try {
      await api("/auth/logout", { method: "POST" });
      setCartAccount(false);
      writeCart([]);
      router.push("/auth/login");
      router.refresh();
    } catch {
      setLogoutError("Chưa đăng xuất được. Hãy thử lại.");
    } finally {
      setLoggingOut(false);
    }
  }
  return (
    <header className="site-header">
      <CartSync />
      <div className="utility-bar wrap">
        <Link href="/sources">Nguồn dữ liệu</Link>
        <nav aria-label="Tiện ích">
          {account?.roles.some((role) =>
            ["admin", "seller"].includes(role),
          ) && (
            <Link href="/manage">
              <Store aria-hidden="true" />
              Kênh quản lý
            </Link>
          )}
          <Link href="/help">
            <Headphones aria-hidden="true" />
            Trợ giúp
          </Link>
          <Link href="/account/orders">
            <PackageCheck aria-hidden="true" />
            Đơn hàng
          </Link>
          {account ? (
            <>
              <Link href="/account/orders">Tài khoản của tôi</Link>
              <button
                type="button"
                className="header-logout"
                disabled={loggingOut}
                onClick={() => void logout()}
              >
                {loggingOut ? "Đang đăng xuất…" : "Đăng xuất"}
              </button>
            </>
          ) : (
            <Link href="/auth/login">Đăng nhập / Đăng ký</Link>
          )}
        </nav>
      </div>
      {logoutError && (
        <p role="alert" className="wrap">
          {logoutError}
        </p>
      )}
      <div className="wrap masthead">
        <Link className="brand" href="/" aria-label="HoodooMart — Trang chủ">
          <span className="brand-mark">h.</span>HoodooMart
        </Link>
        <SearchBar header />
        <nav aria-label="Điều hướng chính">
          <Link href="/account/orders" aria-label="Tài khoản">
            <UserRound aria-hidden="true" />
            <span>Tài khoản</span>
          </Link>
          <Link
            href="/cart"
            aria-label={`Giỏ hàng, ${cart.reduce((n, p) => n + p.quantity, 0)} sản phẩm`}
          >
            <ShoppingBag aria-hidden="true" />
            <span>Giỏ hàng</span>
            <b aria-live="polite">{cart.reduce((n, p) => n + p.quantity, 0)}</b>
          </Link>
        </nav>
      </div>
      <nav className="wrap category-nav" aria-label="Danh mục nhanh">
        <CategoryMenu categories={categories} />
        <Link href="/products">Tất cả sản phẩm</Link>
        {categories
          .filter((c) => c.level === 0)
          .map((c) => (
            <Link key={c.id} href={`/products?category=${c.id}`}>
              {c.name_vi}
            </Link>
          ))}
        <SearchToolButton mode="image" className="inline-tool-link">
          Tìm bằng ảnh
        </SearchToolButton>
        <Link href="/assistant">
          <Sparkles aria-hidden="true" />
          Trợ lý chọn sản phẩm
        </Link>
      </nav>
    </header>
  );
}
