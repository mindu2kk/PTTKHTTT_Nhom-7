import Link from "next/link";
import { Sparkles, Camera, Mic, Search } from "lucide-react";
import { SearchToolButton } from "@/components/unified-search";
export function AiNavigation({
  active,
}: {
  active: "assistant" | "image" | "voice";
}) {
  return (
    <nav className="ai-navigation" aria-label="Công cụ tìm sản phẩm">
      <Link
        href="/assistant"
        aria-current={active === "assistant" ? "page" : undefined}
      >
        <Sparkles aria-hidden="true" />
        Mô tả & so sánh
      </Link>
      <SearchToolButton mode="image">
        <Camera aria-hidden="true" />
        Tìm bằng ảnh
      </SearchToolButton>
      <SearchToolButton mode="voice">
        <Mic aria-hidden="true" />
        Tìm bằng giọng nói
      </SearchToolButton>
      <Link href="/search">
        <Search aria-hidden="true" />
        Tìm từ khóa
      </Link>
    </nav>
  );
}
