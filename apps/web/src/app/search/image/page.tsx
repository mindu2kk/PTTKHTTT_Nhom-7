import { ImageSearch } from "@/components/image-search";
import { serverApi } from "@/lib/server-api";
import type { Category } from "@/lib/api";
import { AiNavigation } from "@/components/ai-navigation";
export default async function ImagePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const initial = await searchParams;
  const categories = await serverApi<Category[]>("/categories");
  return (
    <div className="wrap section-block">
      <AiNavigation active="image" />
      <h1>Tìm bằng hình ảnh</h1>
      <p className="lead">
        Chọn ảnh sản phẩm. Bộ mã hóa OpenCLIP chạy trên máy sẽ so sánh với ảnh
        trong danh mục đã xuất bản.
      </p>
      <ImageSearch categories={categories} initial={initial} />
    </div>
  );
}
