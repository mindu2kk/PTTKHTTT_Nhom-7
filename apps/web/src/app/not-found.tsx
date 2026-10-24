import Link from "next/link";
export default function NotFound() {
  return (
    <div className="wrap section-block empty-state">
      <h1>Không tìm thấy trang</h1>
      <p>Thông tin hiện không khả dụng hoặc đường dẫn đã thay đổi.</p>
      <Link href="/products">Về danh mục sản phẩm</Link>
    </div>
  );
}
