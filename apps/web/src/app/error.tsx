"use client";
import { Button } from "@/components/ui/button";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div className="wrap section-block empty-state">
      <h1>Chưa tải được nội dung</h1>
      <p>Dịch vụ tạm thời chưa sẵn sàng. Hãy thử lại sau ít phút.</p>
      <Button onClick={reset}>Thử lại</Button>
    </div>
  );
}
