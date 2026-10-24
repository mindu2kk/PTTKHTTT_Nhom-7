import type { Metadata } from "next";
import { serverApi } from "@/lib/server-api";
import type { Category } from "@/lib/api";
import { ShoppingAssistant } from "@/components/shopping-assistant";
import { AiNavigation } from "@/components/ai-navigation";
export const metadata: Metadata = { title: "Trợ lý chọn sản phẩm" };
export default async function AssistantPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const [categories, params] = await Promise.all([
    serverApi<Category[]>("/categories"),
    searchParams,
  ]);
  return (
    <div className="wrap section-block assistant-page">
      <AiNavigation active="assistant" />
      <div className="assistant-intro">
        <div>
          <p className="eyebrow">TÌM ĐÚNG MÓN BẠN CẦN</p>
          <h1>Trợ lý chọn sản phẩm</h1>
          <p>Mô tả kiểu dáng, giữ ngân sách, rồi đặt các lựa chọn cạnh nhau.</p>
        </div>
        <p>
          Xử lý trên máy · Không lưu ảnh, âm thanh
          <br />
          Giá và đơn hàng đặt thử
        </p>
      </div>
      <ShoppingAssistant categories={categories} initial={params.q || ""} />
    </div>
  );
}
