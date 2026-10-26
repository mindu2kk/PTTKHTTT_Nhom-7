import { VoiceSearch } from "@/components/voice-search";
import { AiNavigation } from "@/components/ai-navigation";
export default function VoicePage() {
  return (
    <div className="wrap section-block">
      <AiNavigation active="voice" />
      <h1>Tìm bằng giọng nói</h1>
      <p className="lead">
        Nhận giọng tiếng Việt ngay trên máy. Kiểm tra hoặc sửa lại câu đã nhận
        trước khi bấm tìm sản phẩm.
      </p>
      <VoiceSearch />
    </div>
  );
}
