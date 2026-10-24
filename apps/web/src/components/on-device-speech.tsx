"use client";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  localSpeechConstructor,
  localSpeechOptions,
  type LocalSpeech,
  type SpeechAvailability,
} from "@/lib/browser-speech";

export function OnDeviceSpeech({
  disabled,
  onText,
  onActive,
}: {
  disabled: boolean;
  onText(text: string): void;
  onActive(active: boolean): void;
}) {
  const [availability, setAvailability] = useState<
    SpeechAvailability | "checking"
  >("checking");
  const [installing, setInstalling] = useState(false);
  const [listening, setListening] = useState(false);
  const [notice, setNotice] = useState("");
  const recognition = useRef<LocalSpeech | null>(null);
  const cancelled = useRef(false);
  const alive = useRef(true);
  const timeout = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    alive.current = true;
    const Speech = localSpeechConstructor();
    Promise.resolve(
      Speech ? Speech.available(localSpeechOptions) : ("unavailable" as const),
    )
      .then((state) => {
        if (alive.current) setAvailability(state);
      })
      .catch(() => {
        if (alive.current) setAvailability("unavailable");
      });
    return () => {
      alive.current = false;
      cancelled.current = true;
      if (timeout.current) clearTimeout(timeout.current);
      recognition.current?.abort();
    };
  }, []);
  async function install() {
    const Speech = localSpeechConstructor();
    if (!Speech) return;
    setInstalling(true);
    setNotice("");
    try {
      // This download happens only after this explicit, labelled user action.
      const success = await Speech.install(localSpeechOptions);
      if (!alive.current) return;
      setAvailability(await Speech.available(localSpeechOptions));
      setNotice(
        success
          ? "Đã cài gói tiếng Việt. Bạn có thể bắt đầu nói."
          : "Chưa tải được gói tiếng Việt. Hãy thử lại hoặc dùng bản ghi bên dưới.",
      );
    } catch {
      if (alive.current)
        setNotice(
          "Trình duyệt chưa cài được gói tiếng Việt. Bạn có thể dùng bản ghi hoặc nhập câu tìm kiếm.",
        );
    } finally {
      if (alive.current) setInstalling(false);
    }
  }
  function finish(expected?: LocalSpeech) {
    if (expected && recognition.current !== expected) return;
    if (timeout.current) clearTimeout(timeout.current);
    timeout.current = null;
    recognition.current = null;
    if (alive.current) {
      setListening(false);
      onActive(false);
    }
  }
  function start() {
    const Speech = localSpeechConstructor();
    if (!Speech || availability !== "available") return;
    const rec = new Speech();
    recognition.current = rec;
    cancelled.current = false;
    rec.lang = "vi-VN";
    rec.processLocally = true;
    rec.continuous = false;
    rec.interimResults = false;
    rec.onresult = (event) => {
      if (!alive.current || cancelled.current || recognition.current !== rec)
        return;
      const text = Array.from(event.results)
        .map((result) => result[0].transcript)
        .join(" ")
        .trim();
      if (text) {
        onText(text.slice(0, 300));
        setNotice(
          "Đã nhận câu nói trên thiết bị. Hãy kiểm tra rồi tìm sản phẩm.",
        );
      }
    };
    rec.onerror = (event) => {
      if (!alive.current || cancelled.current || recognition.current !== rec)
        return;
      setNotice(
        event.error === "not-allowed"
          ? "Chưa được cấp quyền micro. Hãy cho phép hoặc nhập văn bản."
          : event.error === "language-not-supported"
            ? "Gói tiếng Việt chưa sẵn sàng trong phiên trình duyệt này. Hãy tải lại gói hoặc dùng bản ghi bên dưới."
            : "Chưa nghe rõ câu nói. Hãy thử lại, dùng bản ghi hoặc nhập văn bản.",
      );
      if (event.error === "language-not-supported")
        setAvailability("downloadable");
      finish(rec);
    };
    rec.onend = () => finish(rec);
    setNotice("");
    try {
      rec.start();
      setListening(true);
      onActive(true);
      timeout.current = setTimeout(() => {
        rec.stop();
        timeout.current = setTimeout(() => {
          if (recognition.current !== rec) return;
          cancelled.current = true;
          rec.abort();
          finish(rec);
          setNotice(
            "Chưa nhận được câu nói trong thời gian cho phép. Hãy dùng bản ghi hoặc nhập văn bản.",
          );
        }, 3000);
      }, 12000);
    } catch {
      finish(rec);
      setNotice(
        "Chưa bắt đầu được nhận giọng. Hãy dùng bản ghi hoặc nhập văn bản.",
      );
    }
  }
  return (
    <section
      aria-label="Nhận giọng trên thiết bị"
      className="mb-6 border-b pb-6"
    >
      <h2 className="text-lg font-semibold">Nhận giọng nhẹ trên trình duyệt</h2>
      <p>
        Không cần khóa API, không gửi âm thanh lên dịch vụ. Trình duyệt xử lý
        trên thiết bị của bạn; cần tải gói tiếng Việt một lần và vẫn dùng
        CPU/RAM của thiết bị.
      </p>
      <p className="text-sm text-muted-foreground">
        Tính năng thử nghiệm, tùy phiên bản trình duyệt. Nếu chưa nhận được câu
        nói, hãy dùng bản ghi hoặc nhập văn bản.
      </p>
      {availability === "checking" && (
        <p role="status">Đang kiểm tra hỗ trợ tiếng Việt…</p>
      )}
      {availability === "unavailable" && (
        <p>
          Trình duyệt này chưa hỗ trợ nhận giọng tiếng Việt trên thiết bị. Bạn
          có thể dùng bản ghi cục bộ bên dưới hoặc nhập văn bản.
        </p>
      )}
      <div className="media-actions">
        {(availability === "downloadable" ||
          availability === "downloading") && (
          <Button onClick={install} disabled={disabled || installing}>
            {installing
              ? "Đang tải gói tiếng Việt…"
              : "Tải gói tiếng Việt (một lần)"}
          </Button>
        )}
        {availability === "available" && (
          <Button
            onClick={listening ? () => recognition.current?.stop() : start}
            disabled={disabled || installing}
          >
            {listening ? "Dừng nhận giọng" : "Bắt đầu nhận giọng trên thiết bị"}
          </Button>
        )}
        {listening && (
          <Button
            variant="outline"
            onClick={() => {
              cancelled.current = true;
              recognition.current?.abort();
              finish();
              setNotice("Đã hủy nhận giọng.");
            }}
          >
            Hủy nhận giọng
          </Button>
        )}
      </div>
      {listening && (
        <p role="status">Đang nghe trên thiết bị · tự dừng sau 12 giây</p>
      )}
      {notice && <p role="status">{notice}</p>}
    </section>
  );
}
