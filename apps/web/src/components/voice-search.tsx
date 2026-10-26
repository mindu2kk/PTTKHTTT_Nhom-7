"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { OnDeviceSpeech } from "@/components/on-device-speech";
import { MicrophoneInput } from "@/components/microphone-input";
type Transcript = {
  text: string;
  duration_seconds: number;
  inference_ms: number;
  warnings: string[];
};
export function VoiceSearch() {
  const [recording, setRecording] = useState(false);
  const [deviceActive, setDeviceActive] = useState(false);
  const [micPending, setMicPending] = useState(false);
  const alive = useRef(true);
  const [seconds, setSeconds] = useState(0);
  const [microphone, setMicrophone] = useState("");
  const [activeStream, setActiveStream] = useState<MediaStream | null>(null);
  const [file, setFile] = useState<File>();
  const [preview, setPreview] = useState("");
  const [text, setText] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Transcript>();
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const abort = useRef<AbortController | null>(null);
  const picker = useRef<HTMLInputElement>(null);
  function release() {
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
    setActiveStream(null);
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  }
  useEffect(() => {
    alive.current = true;
    return () => {
      alive.current = false;
      release();
      abort.current?.abort();
      if (recorder.current?.state === "recording") {
        recorder.current.onstop = null;
        recorder.current.stop();
      }
    };
  }, []);
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview);
    },
    [preview],
  );
  function choose(selected?: File) {
    abort.current?.abort();
    setBusy(false);
    setError("");
    setText("");
    setResult(undefined);
    setFile(undefined);
    setPreview("");
    if (!selected) return;
    if (selected.size > 2 * 1024 * 1024) {
      setError("Âm thanh tối đa 2 MB và 15 giây.");
      return;
    }
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
  }
  function stop() {
    if (recorder.current?.state === "recording") recorder.current.stop();
    release();
    setRecording(false);
  }
  async function start() {
    setError("");
    if (
      !window.isSecureContext ||
      !navigator.mediaDevices?.getUserMedia ||
      !window.MediaRecorder
    ) {
      setError(
        "Trình duyệt chưa hỗ trợ ghi âm ở trang này. Hãy tải tệp hoặc nhập văn bản.",
      );
      return;
    }
    try {
      setMicPending(true);
      const media = await navigator.mediaDevices.getUserMedia({
        audio: {
          ...(microphone ? { deviceId: { exact: microphone } } : {}),
          channelCount: 1,
          autoGainControl: true,
          echoCancellation: true,
          noiseSuppression: true,
        },
        video: false,
      });
      if (!alive.current) {
        media.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = media;
      setActiveStream(media);
      const mime = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ].find((t) => MediaRecorder.isTypeSupported(t));
      const rec = new MediaRecorder(
        media,
        mime ? { mimeType: mime } : undefined,
      );
      recorder.current = rec;
      const chunks: Blob[] = [];
      rec.ondataavailable = (e) => {
        if (e.data.size) chunks.push(e.data);
      };
      rec.onstop = () => {
        release();
        setRecording(false);
        const type = rec.mimeType.split(";")[0];
        const ext = type.includes("ogg")
          ? "ogg"
          : type.includes("mp4")
            ? "m4a"
            : "webm";
        choose(new File(chunks, `ban-ghi.${ext}`, { type }));
      };
      rec.onerror = () => {
        release();
        setRecording(false);
        setError("Ghi âm bị gián đoạn. Hãy thử lại hoặc tải tệp.");
      };
      choose();
      setSeconds(0);
      setRecording(true);
      rec.start(250);
      let elapsed = 0;
      timer.current = setInterval(() => {
        elapsed += 1;
        setSeconds(elapsed);
        if (elapsed >= 12) stop();
      }, 1000);
    } catch {
      release();
      setError(
        "Chưa được cấp quyền micro. Hãy cho phép trong trình duyệt, tải tệp hoặc nhập văn bản.",
      );
    } finally {
      if (alive.current) setMicPending(false);
    }
  }
  async function transcribe() {
    if (!file) return;
    const controller = new AbortController();
    abort.current = controller;
    setBusy(true);
    setError("");
    const body = new FormData();
    body.set("audio", file);
    try {
      const data = await api<Transcript>("/search/voice", {
        method: "POST",
        body,
        signal: controller.signal,
      });
      if (!controller.signal.aborted) {
        setResult(data);
        setText(data.text);
      }
    } catch (e) {
      if (!controller.signal.aborted)
        setError(e instanceof Error ? e.message : "Chưa nhận được giọng nói.");
    } finally {
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  return (
    <div className="voice-panel">
      <OnDeviceSpeech
        disabled={recording || busy || micPending}
        onActive={setDeviceActive}
        onText={(value) => {
          setText(value);
          setResult(undefined);
          setError("");
        }}
      />
      <h2 className="text-lg font-semibold">Dùng bản ghi với Whisper cục bộ</h2>
      <p>
        Lựa chọn dự phòng khi trình duyệt chưa hỗ trợ. Mô hình chạy trên máy chủ
        cục bộ, cần nhiều tài nguyên hơn; hãy kiểm tra bản chép lời.
      </p>
      <div className="media-actions">
        <MicrophoneInput
          stream={recording ? activeStream : null}
          deviceId={microphone}
          onChange={setMicrophone}
          disabled={recording || busy || micPending || deviceActive}
        />
        <Button
          onClick={recording ? stop : start}
          disabled={busy || micPending || deviceActive}
        >
          {recording ? `Dừng ghi · ${seconds}s` : "Bắt đầu ghi âm"}
        </Button>
        {recording && (
          <Button
            variant="outline"
            onClick={() => {
              if (recorder.current) {
                recorder.current.onstop = null;
                recorder.current.stop();
              }
              release();
              setRecording(false);
              choose();
            }}
          >
            Hủy bản ghi
          </Button>
        )}
        <Button
          variant="outline"
          onClick={() => picker.current?.click()}
          disabled={recording || busy || deviceActive}
        >
          Chọn tệp âm thanh
        </Button>
        <input
          ref={picker}
          className="sr-only"
          type="file"
          aria-label="Tệp âm thanh"
          accept=".wav,.webm,.ogg,.m4a,.mp4"
          onChange={(e) => choose(e.target.files?.[0])}
        />
      </div>
      <p>
        Chỉ ghi khi bạn bấm nút. Tự dừng sau 12 giây; WAV, WebM, Ogg hoặc M4A
        tối đa 2 MB. Bản ghi không được lưu lại.
      </p>
      {recording && <p role="status">Đang ghi âm · {seconds} giây</p>}
      {preview && (
        <div>
          <p>{file?.name}</p>
          <audio controls src={preview} />
          <Button onClick={transcribe} disabled={busy || recording}>
            {busy ? "Đang chuyển thành chữ…" : "Chuyển thành chữ"}
          </Button>
        </div>
      )}
      {busy && (
        <Button
          variant="outline"
          onClick={() => {
            abort.current?.abort();
            setBusy(false);
          }}
        >
          Hủy xử lý
        </Button>
      )}
      {error && <p role="alert">{error}</p>}
      {result && (
        <p role="status">
          Bản ghi {result.duration_seconds}s · xử lý{" "}
          {(result.inference_ms / 1000).toFixed(1)}s.{" "}
          {result.warnings.join(" ")}
        </p>
      )}
      <form action="/search" method="get" className="voice-form">
        <input type="hidden" name="modality" value="voice" />
        <label htmlFor="transcript">Kiểm tra và sửa câu tìm kiếm</label>
        <textarea
          id="transcript"
          name="q"
          value={text}
          onChange={(e) => setText(e.target.value)}
          required
          maxLength={300}
          rows={3}
          placeholder="Bạn cũng có thể nhập trực tiếp tại đây"
        />
        <Button
          type="submit"
          disabled={!text.trim() || recording || deviceActive}
        >
          Tìm bằng câu đã sửa
        </Button>
      </form>
      <Link href="/search">Quay về tìm bằng văn bản</Link>
      {text.trim() && (
        <Link href={`/assistant?q=${encodeURIComponent(text.trim())}`}>
          Tìm theo hình dáng từ câu đã sửa
        </Link>
      )}
    </div>
  );
}
