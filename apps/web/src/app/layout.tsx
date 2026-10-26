import type { Metadata } from "next";
import { Suspense } from "react";
import Link from "next/link";
import Image from "next/image";
import { SiteHeader } from "@/components/site-header";
import { serverApi } from "@/lib/server-api";
import type { Category } from "@/lib/api";
import { UnifiedSearch } from "@/components/unified-search";
import "./globals.css";
import "./storefront.css";
import "./media.css";
import "./marketplace.css";
import "./marketplace-ai.css";
import "./inline-search.css";
export const metadata: Metadata = {
  title: {
    default: "Hoodoo — Tìm theo cách của bạn",
    template: "%s | Hoodoo",
  },
  description:
    "Khám phá sản phẩm bằng văn bản, giọng nói hoặc hình ảnh. Ảnh và dữ liệu có nguồn gốc; đơn hàng đặt thử.",
};
export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [categories, account] = await Promise.all([
    serverApi<Category[]>("/categories").catch(() => []),
    serverApi<{ roles: string[] }>("/auth/me").catch(() => null),
  ]);
  return (
    <html lang="vi">
      <body>
        <a href="#main" className="skip-link">
          Đến nội dung chính
        </a>
        <SiteHeader categories={categories} account={account} />
        <Suspense fallback={null}>
          <UnifiedSearch categories={categories} />
        </Suspense>
        <main id="main">{children}</main>
        <footer>
          <div className="wrap footer-grid">
            <div>
              <Link className="brand brand-logo footer-logo" href="/">
                <Image
                  src="/images/brand/hoodoo-white-on-black.png"
                  alt="Hoodoo"
                  width={2048}
                  height={768}
                  sizes="148px"
                />
              </Link>
              <p>Tìm theo cách của bạn.</p>
            </div>
            <nav aria-label="Liên kết cuối trang">
              <Link href="/products">Danh mục sản phẩm</Link>
              <Link href="/assistant">Trợ lý chọn sản phẩm</Link>
              <Link href="/cart">Giỏ hàng</Link>
              <Link href="/account/orders">Đơn hàng của tôi</Link>
              <Link href="/sources">Nguồn dữ liệu và ảnh</Link>
              <Link href="/help">Trợ giúp & quyền riêng tư</Link>
            </nav>
            <p>
              Ảnh sản phẩm được sử dụng theo quyền của từng nguồn; xem trang
              nguồn dữ liệu để biết chi tiết. Giá và hạn mức đặt thử được mô
              phỏng riêng.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
