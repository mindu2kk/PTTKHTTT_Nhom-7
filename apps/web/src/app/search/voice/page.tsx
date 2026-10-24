import { VoiceSearch } from "@/components/voice-search";
import { AiNavigation } from "@/components/ai-navigation";
export default function VoicePage() {
  return (
    <div className="wrap section-block">
      <AiNavigation active="voice" />
      <h1>Tìm bằng giọng nói</h1>
      <p className="lead">
        Nhận giọng tiếng Việt trên thiết bị khi trình duyệt hỗ trợ, hoặc dùng
        Whisper cục bộ. Kiểm tra câu đã nhận trước khi tìm sản phẩm.
      </p>
      <VoiceSearch />
    </div>
  );
}
