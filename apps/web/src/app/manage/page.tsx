import Link from "next/link";
import { ApiError, serverApi } from "@/lib/server-api";
import type { Account } from "@/lib/commerce";
import type { Category } from "@/lib/api";
import { ManageProducts, type Managed } from "@/components/manage-products";
export default async function Manage() {
  let account: Account;
  let data: Managed;
  let categories: Category[];
  let images: { items: { id: string; url: string; alt: string }[] };
  try {
    [account, data, categories, images] = await Promise.all([
      serverApi<Account>("/auth/me"),
      serverApi<Managed>("/manage/products"),
      serverApi<Category[]>("/categories"),
      serverApi<{ items: { id: string; url: string; alt: string }[] }>(
        "/manage/images",
      ),
    ]);
  } catch (e) {
    if (e instanceof ApiError && [401, 403].includes(e.status))
      return (
        <div className="wrap section-block">
          <h1>Khu vực quản lý</h1>
          <p>Cần tài khoản người bán đã duyệt hoặc quản trị viên.</p>
          <Link href="/auth/login">Đăng nhập</Link>
        </div>
      );
    throw e;
  }
  return (
    <div className="wrap section-block">
      <h1>Quản lý sản phẩm</h1>
      <ManageProducts
        data={data}
        categories={categories}
        admin={account.roles.includes("admin")}
        images={images.items}
      />
    </div>
  );
}
