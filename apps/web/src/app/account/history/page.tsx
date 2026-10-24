import Link from "next/link";
import { ApiError, serverApi } from "@/lib/server-api";
export default async function History() {
  let items: {
    id: string;
    text: string;
    modality: string;
    created_at: string;
  }[];
  try {
    items = await serverApi("/history");
  } catch (e) {
    if (e instanceof ApiError && e.status === 401)
      return (
        <div className="wrap section-block">
          <h1>Lịch sử tìm kiếm</h1>
          <Link href="/auth/login">Đăng nhập</Link>
        </div>
      );
    throw e;
  }
  return (
    <div className="wrap section-block narrow">
      <h1>Lịch sử tìm kiếm</h1>
      <p>
        Chỉ lưu khi bạn bật trong tài khoản. Tối đa 100 câu, tự hết hạn sau 7
        ngày; không lưu tệp tải lên.
      </p>
      {items.length ? (
        <ul>
          {items.map((i) => (
            <li key={i.id}>
              <Link href={`/search?q=${encodeURIComponent(i.text)}`}>
                {i.text}
              </Link>{" "}
              · {new Date(i.created_at).toLocaleString("vi-VN")}
            </li>
          ))}
        </ul>
      ) : (
        <p>Chưa có lịch sử tìm kiếm.</p>
      )}
      <Link href="/account/orders">Cài đặt tài khoản và xóa lịch sử</Link>
    </div>
  );
}
