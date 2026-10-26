"use client";
import Link from "next/link";
import Image from "next/image";
import {
  ShoppingBag,
  UserRound,
  Headphones,
  Store,
  PackageCheck,
  Sparkles,
  ChevronDown,
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
  const [openCategory, setOpenCategory] = useState<string | null>(null);
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
        <Link
          className="brand brand-logo"
          href="/"
          aria-label="Hoodoo — Trang chủ"
        >
          <Image
            src="/images/brand/hoodoo-white-on-black.png"
            alt="Hoodoo"
            width={2048}
            height={768}
            sizes="(max-width: 768px) 240px, 304px"
            priority
          />
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
          .filter((c) => c.parent_id === "nam")
          .map((group) => (
            <div
              key={group.id}
              className="nav-category"
              onPointerEnter={(event) => {
                if (event.pointerType === "mouse") setOpenCategory(group.id);
              }}
              onPointerLeave={(event) => {
                if (event.pointerType === "mouse") setOpenCategory(null);
              }}
              onBlur={(event) => {
                if (!event.currentTarget.contains(event.relatedTarget))
                  setOpenCategory(null);
              }}
              onKeyDown={(event) => {
                if (event.key === "Escape") {
                  setOpenCategory(null);
                  event.currentTarget.querySelector("button")?.focus();
                }
              }}
            >
              <button
                type="button"
                className="nav-category-trigger"
                aria-expanded={openCategory === group.id}
                aria-controls={`nav-category-${group.id}`}
                onClick={() =>
                  setOpenCategory(openCategory === group.id ? null : group.id)
                }
              >
                {group.name_vi}
                <ChevronDown aria-hidden="true" />
              </button>
              <div
                id={`nav-category-${group.id}`}
                className="nav-category-panel"
                hidden={openCategory !== group.id}
              >
                <Link
                  href={`/products?category=${group.id}`}
                  onClick={() => setOpenCategory(null)}
                >
                  Xem tất cả {group.name_vi.toLocaleLowerCase("vi-VN")}
                </Link>
                {categories
                  .filter((c) => c.parent_id === group.id)
                  .map((leaf) => (
                    <Link
                      key={leaf.id}
                      href={`/products?category=${leaf.id}`}
                      onClick={() => setOpenCategory(null)}
                    >
                      {leaf.name_vi}
                    </Link>
                  ))}
              </div>
            </div>
          ))}
        {account?.roles.includes("admin") && (
          <Link href="/manage">Quản lý sản phẩm</Link>
        )}
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
