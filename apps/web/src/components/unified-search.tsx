"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { Camera, Mic, Search, Square, X } from "lucide-react";
import { api, ApiClientError, money, type Category } from "@/lib/api";
import type { components } from "@/lib/schema";
import {
  SEARCH_OPEN,
  SEARCH_QUERY,
  type SearchLaunch,
  openSearch,
} from "@/lib/unified-search";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ProductCard } from "@/components/product-card";
import { OrderCard } from "@/components/order-card";
import {
  clipboardImage,
  imageInputError,
  searchBudget,
} from "@/lib/search-input";

type Products = components["schemas"]["SearchResponse"];
type Result = Products | components["schemas"]["OrderSearchResponse"];
type Transcript = components["schemas"]["TranscriptResponse"];
type Phase = "idle" | "permission" | "recording" | "transcribing" | "searching";
type Snapshot = {
  query: string;
  mode: "text" | "voice" | "image";
  file?: File;
  category: string;
  budget: string;
};

export function SearchToolButton({
  mode,
  children,
  className,
}: {
  mode: "voice" | "image";
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <button
      type="button"
      className={className}
      onClick={() => openSearch({ mode })}
    >
      {children}
    </button>
  );
}

export function UnifiedSearch({ categories }: { categories: Category[] }) {
  const pathname = usePathname();
  const params = useSearchParams();
  return (
    <SearchSession
      key={`${pathname}?${params.toString()}`}
      categories={categories}
    />
  );
}

function SearchSession({ categories }: { categories: Category[] }) {
  const [opened, setOpened] = useState(false);
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<Snapshot["mode"]>("text");
  const [phase, setPhase] = useState<Phase>("idle");
  const [seconds, setSeconds] = useState(0);
  const [preview, setPreview] = useState("");
  const [fileName, setFileName] = useState("");
  const [category, setCategory] = useState("");
  const [budget, setBudget] = useState("");
  const [error, setError] = useState("");
  const [authError, setAuthError] = useState(false);
  const [notice, setNotice] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [result, setResult] = useState<Result>();
  const epoch = useRef(0);
  const abort = useRef<AbortController | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const image = useRef<File | undefined>(undefined);
  const objectUrl = useRef("");
  const last = useRef<Snapshot | null>(null);
  const field = useRef<HTMLInputElement>(null);
  const picker = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLElement | null>(null);

  const release = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
  }, []);
  const invalidate = useCallback(() => {
    epoch.current += 1;
    abort.current?.abort();
    abort.current = null;
    if (recorder.current) {
      recorder.current.onstop = null;
      recorder.current.ondataavailable = null;
      recorder.current.onerror = null;
      if (recorder.current.state === "recording") recorder.current.stop();
      recorder.current = null;
    }
    release();
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current);
    objectUrl.current = "";
    image.current = undefined;
    last.current = null;
  }, [release]);
  useEffect(() => invalidate, [invalidate]);
  useEffect(() => {
    if (phase !== "recording" && phase !== "permission") return;
    const hidden = () => {
      if (document.hidden) {
        invalidate();
        setPhase("idle");
        setNotice("Đã dừng ghi âm khi bạn rời trang.");
      }
    };
    document.addEventListener("visibilitychange", hidden);
    return () => document.removeEventListener("visibilitychange", hidden);
  }, [phase, invalidate]);

  const updateQuery = useCallback((value: string) => {
    setQuery(value);
    setSuggestions([]);
    window.dispatchEvent(new CustomEvent(SEARCH_QUERY, { detail: value }));
  }, []);

  const find = useCallback(async (snapshot: Snapshot, page = 1) => {
    if (!snapshot.file && !snapshot.query.trim()) {
      setError("Hãy nhập từ khóa, ghi âm hoặc chọn ảnh.");
      return;
    }
    const attempt = ++epoch.current;
    abort.current?.abort();
    const controller = new AbortController();
    abort.current = controller;
    last.current = snapshot;
    setPhase("searching");
    setError("");
    setAuthError(false);
    setNotice("");
    setResult(undefined);
    try {
      let response: Result;
      const filters = {
        ...(snapshot.category ? { category: snapshot.category } : {}),
        ...(snapshot.budget !== ""
          ? { price_max: Number(snapshot.budget) }
          : {}),
        page,
        page_size: 12,
      };
      if (snapshot.file) {
        const body = new FormData();
        body.set("image", snapshot.file);
        body.set("text", snapshot.query.trim());
        for (const [key, value] of Object.entries(filters))
          body.set(key, String(value));
        response = await api<Products>("/search/image", {
          method: "POST",
          body,
          signal: controller.signal,
        });
      } else {
        response = await api<Result>("/search/text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            q: snapshot.query.trim(),
            modality: snapshot.mode === "voice" ? "voice" : "text",
            ...filters,
          }),
          signal: controller.signal,
        });
      }
      if (attempt === epoch.current) setResult(response);
    } catch (reason) {
      if (attempt === epoch.current && !controller.signal.aborted) {
        setAuthError(reason instanceof ApiClientError && reason.status === 401);
        setError(
          reason instanceof ApiClientError
            ? reason.message
            : "Chưa kết nối được tìm kiếm. Hãy thử lại.",
        );
      }
    } finally {
      if (attempt === epoch.current) setPhase("idle");
    }
  }, []);

  const chooseImage = useCallback(
    (file: File) => {
      invalidate();
      setPreview("");
      setFileName("");
      setResult(undefined);
      setError("");
      setAuthError(false);
      setNotice("");
      setSuggestions([]);
      setPhase("idle");
      setMode("image");
      setOpened(true);
      const inputError = imageInputError(file);
      if (inputError) {
        setError(inputError);
        return;
      }
      const extension =
        file.type === "image/jpeg"
          ? "jpg"
          : file.type === "image/webp"
            ? "webp"
            : "png";
      image.current =
        !file.name || file.name === "blob"
          ? new File([file], `anh-da-dan.${extension}`, { type: file.type })
          : file;
      objectUrl.current = URL.createObjectURL(file);
      setPreview(objectUrl.current);
      setFileName(image.current.name);
    },
    [invalidate],
  );

  const startVoice = useCallback(async () => {
    invalidate();
    setPreview("");
    setFileName("");
    setResult(undefined);
    setError("");
    setAuthError(false);
    setNotice("");
    setSuggestions([]);
    setMode("voice");
    setOpened(true);
    setSeconds(0);
    if (
      !window.isSecureContext ||
      !navigator.mediaDevices?.getUserMedia ||
      !window.MediaRecorder
    ) {
      setPhase("idle");
      setError(
        "Trình duyệt chưa hỗ trợ ghi âm ở đây. Hãy dùng Chrome trên localhost/HTTPS hoặc nhập chữ.",
      );
      return;
    }
    setPhase("permission");
    const attempt = epoch.current;
    try {
      const tracks = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
        video: false,
      });
      if (attempt !== epoch.current) {
        tracks.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = tracks;
      const mimeType = [
        "audio/webm;codecs=opus",
        "audio/ogg;codecs=opus",
        "audio/mp4",
      ].find((type) => MediaRecorder.isTypeSupported(type));
      const rec = new MediaRecorder(
        tracks,
        mimeType ? { mimeType } : undefined,
      );
      recorder.current = rec;
      const chunks: Blob[] = [];
      let size = 0;
      rec.ondataavailable = (event) => {
        if (attempt !== epoch.current) return;
        size += event.data.size;
        if (size > 2 * 1024 * 1024) {
          invalidate();
          setPhase("idle");
          setError("Bản ghi vượt 2 MB. Hãy nói một câu ngắn hơn.");
          return;
        }
        if (event.data.size) chunks.push(event.data);
      };
      rec.onerror = () => {
        if (attempt === epoch.current) {
          invalidate();
          setPhase("idle");
          setError("Ghi âm bị gián đoạn. Hãy thử lại.");
        }
      };
      rec.onstop = async () => {
        release();
        if (attempt !== epoch.current) return;
        recorder.current = null;
        if (!size) {
          setPhase("idle");
          setError("Chưa ghi được âm thanh. Hãy thử lại.");
          return;
        }
        setPhase("transcribing");
        const controller = new AbortController();
        abort.current = controller;
        const type = rec.mimeType.split(";")[0];
        const ext = type.includes("ogg")
          ? "ogg"
          : type.includes("mp4")
            ? "m4a"
            : "webm";
        const body = new FormData();
        body.set("audio", new File(chunks, `ban-ghi.${ext}`, { type }));
        try {
          const data = await api<Transcript>("/search/voice", {
            method: "POST",
            body,
            signal: controller.signal,
          });
          if (attempt === epoch.current) {
            updateQuery(data.text);
            setSuggestions(data.suggestions ?? []);
            setNotice(
              data.warnings.join(" ") ||
                "Đã nhận câu nói. Kiểm tra hoặc sửa rồi bấm Tìm.",
            );
          }
        } catch (reason) {
          if (attempt === epoch.current && !controller.signal.aborted)
            setError(
              reason instanceof ApiClientError
                ? reason.message
                : "Chưa nhận được câu nói. Hãy thử lại hoặc nhập chữ.",
            );
        } finally {
          if (attempt === epoch.current) setPhase("idle");
        }
      };
      rec.start(200);
      setPhase("recording");
      const started = performance.now();
      timer.current = setInterval(() => {
        const elapsed = Math.floor((performance.now() - started) / 1000);
        setSeconds(elapsed);
        if (elapsed >= 12 && rec.state === "recording") {
          rec.stop();
          release();
        }
      }, 200);
    } catch {
      if (attempt === epoch.current) {
        release();
        setPhase("idle");
        setError(
          "Chưa được cấp quyền micro. Cho phép trong trình duyệt hoặc nhập chữ để tìm.",
        );
      }
    }
  }, [invalidate, release, updateQuery]);

  useEffect(() => {
    const launch = (event: Event) => {
      const detail = (event as CustomEvent<SearchLaunch>).detail;
      if (!detail || !["text", "voice", "image"].includes(detail.mode)) return;
      opener.current =
        document.activeElement instanceof HTMLElement
          ? document.activeElement
          : null;
      invalidate();
      setPhase("idle");
      setMode(detail.mode);
      setOpened(true);
      setResult(undefined);
      setError("");
      setAuthError(false);
      setNotice("");
      setPreview("");
      setFileName("");
      const text =
        typeof detail.query === "string" ? detail.query.slice(0, 300) : "";
      updateQuery(text);
      const params = new URLSearchParams(location.search);
      const currentCategory = params.get("category") || "";
      const selectedCategory = categories.some((c) => c.id === currentCategory)
        ? currentCategory
        : "";
      const currentBudget = params.get("price_max") || "";
      const selectedBudget = searchBudget(currentBudget);
      setCategory(selectedCategory);
      setBudget(selectedBudget);
      if (detail.mode === "voice") void startVoice();
      else if (detail.file instanceof File) chooseImage(detail.file);
      else if (detail.mode === "text" && text.trim())
        void find({
          query: text,
          mode: "text",
          category: selectedCategory,
          budget: selectedBudget,
        });
    };
    window.addEventListener(SEARCH_OPEN, launch);
    return () => window.removeEventListener(SEARCH_OPEN, launch);
  }, [categories, chooseImage, find, invalidate, startVoice, updateQuery]);

  function close() {
    invalidate();
    setOpened(false);
    setPhase("idle");
    setPreview("");
    setFileName("");
    setResult(undefined);
    setError("");
    setNotice("");
    setSuggestions([]);
  }
  function paste(event: React.ClipboardEvent) {
    const file = clipboardImage(event.clipboardData.items);
    if (file) {
      event.preventDefault();
      chooseImage(file);
    }
  }
  const busy = phase !== "idle";
  return (
    <Dialog
      open={opened}
      onOpenChange={(value) => {
        if (!value) close();
      }}
    >
      <DialogContent
        className="unified-search-dialog"
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          if (opener.current?.isConnected) opener.current.focus();
        }}
        onPaste={paste}
      >
        <DialogHeader>
          <DialogTitle>Tìm sản phẩm</DialogTitle>
          <DialogDescription className="sr-only">
            Nhập chữ, thu âm hoặc chọn và dán ảnh. Kết quả hiển thị tại trang
            hiện tại.
          </DialogDescription>
        </DialogHeader>
        <form
          className="unified-search-controls"
          onSubmit={(event) => {
            event.preventDefault();
            void find({ query, mode, file: image.current, category, budget });
          }}
        >
          <div className="unified-query-row">
            <label className="sr-only" htmlFor="inline-query">
              Câu tìm kiếm
            </label>
            <input
              ref={field}
              id="inline-query"
              value={query}
              onChange={(event) => updateQuery(event.target.value)}
              maxLength={300}
              placeholder={
                mode === "image"
                  ? "Mô tả thêm cho ảnh (không bắt buộc)"
                  : "Bạn đang tìm gì?"
              }
              disabled={busy}
            />
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Ghi âm tại đây"
              disabled={busy}
              onClick={() => void startVoice()}
            >
              <Mic />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              aria-label="Chọn ảnh tại đây"
              disabled={busy}
              onClick={() => {
                setMode("image");
                picker.current?.click();
              }}
            >
              <Camera />
            </Button>
            <Button
              type="submit"
              disabled={busy || (!query.trim() && !preview)}
            >
              <Search data-icon="inline-start" />
              Tìm
            </Button>
          </div>
          <input
            className="sr-only"
            tabIndex={-1}
            ref={picker}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            aria-label="Ảnh tìm kiếm tại chỗ"
            onChange={(event) => {
              const file = event.target.files?.[0];
              event.target.value = "";
              if (file) chooseImage(file);
            }}
          />
          {mode === "image" && (
            <div
              className="inline-image-area"
              onDragOver={(event) => event.preventDefault()}
              onDrop={(event) => {
                event.preventDefault();
                const file = event.dataTransfer.files[0];
                if (file) chooseImage(file);
              }}
            >
              {preview ? (
                <>
                  <Image
                    src={preview}
                    alt="Ảnh bạn chọn để tìm kiếm"
                    width={96}
                    height={96}
                    unoptimized
                  />
                  <span>{fileName}</span>
                  <Button
                    type="button"
                    variant="ghost"
                    aria-label="Xóa ảnh đã chọn"
                    disabled={busy}
                    onClick={() => {
                      invalidate();
                      setPreview("");
                      setFileName("");
                      setResult(undefined);
                    }}
                  >
                    <X />
                  </Button>
                </>
              ) : (
                <>
                  <Camera aria-hidden="true" />
                  <span>Thả ảnh hoặc dán Ctrl+V · tối đa 5 MB</span>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => picker.current?.click()}
                    disabled={busy}
                  >
                    Chọn ảnh
                  </Button>
                </>
              )}
            </div>
          )}
          <details className="inline-search-filters">
            <summary>
              Bộ lọc
              {category &&
                ` · ${categories.find((c) => c.id === category)?.name_vi || "Đã chọn danh mục"}`}
              {budget !== "" &&
                Number(budget) >= 0 &&
                Number(budget) <= 1e12 &&
                ` · Đến ${money(Number(budget))}`}
            </summary>
            <div>
              <label>
                Danh mục
                <select
                  value={category}
                  disabled={busy}
                  onChange={(event) => setCategory(event.target.value)}
                >
                  <option value="">Tất cả danh mục</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>
                      {"— ".repeat(c.level)}
                      {c.name_vi}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Giá tối đa (₫)
                <input
                  type="number"
                  min={0}
                  max={1e12}
                  step={1}
                  value={budget}
                  disabled={busy}
                  onChange={(event) => setBudget(event.target.value)}
                />
              </label>
            </div>
          </details>
        </form>
        <div className="inline-search-status">
          {phase === "permission" && <p role="status">Đang chờ quyền micro…</p>}
          {phase === "recording" && (
            <>
              <p role="status">
                <Mic aria-hidden="true" />
                Đang ghi âm · {seconds}s / 12s
              </p>
              <Button
                type="button"
                onClick={() => {
                  if (recorder.current?.state === "recording") {
                    recorder.current.stop();
                    release();
                  }
                }}
              >
                <Square data-icon="inline-start" />
                Dừng và nhận câu nói
              </Button>
            </>
          )}
          {phase === "transcribing" && <p role="status">Đang nhận câu nói…</p>}
          {phase === "searching" && <p role="status">Đang tìm sản phẩm…</p>}
          {busy && (
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                invalidate();
                setPhase("idle");
                setPreview("");
                setFileName("");
                setNotice("Đã hủy. Bạn có thể nhập chữ hoặc thử lại.");
              }}
            >
              Hủy xử lý
            </Button>
          )}
          {notice && <p role="status">{notice}</p>}
          {suggestions.length > 0 && phase === "idle" && (
            <div
              className="inline-voice-alternatives"
              aria-label="Gợi ý từ gần âm"
            >
              <p>Có phải bạn muốn tìm?</p>
              {suggestions.map((value) => (
                <Button
                  key={value}
                  type="button"
                  variant="outline"
                  onClick={() => {
                    updateQuery(value);
                    setNotice("Đã chọn câu gợi ý. Kiểm tra rồi bấm Tìm.");
                    field.current?.focus();
                  }}
                >
                  {value}
                </Button>
              ))}
            </div>
          )}
          {error && (
            <p role="alert">
              {error}
              {authError && (
                <>
                  {" "}
                  <Link href="/auth/login" onClick={close}>
                    Đăng nhập
                  </Link>
                </>
              )}
            </p>
          )}
        </div>
        <div
          className="inline-search-results"
          aria-busy={phase === "searching"}
        >
          {phase === "searching" && (
            <div className="product-grid">
              {Array.from({ length: 6 }, (_, i) => (
                <Skeleton className="h-48" key={i} />
              ))}
            </div>
          )}
          {result?.search_type === "order" && (
            <OrderCard order={result.order} />
          )}
          {result?.search_type === "products" && (
            <>
              <p role="status" className="inline-result-count">
                {result.total} sản phẩm · trang {result.page}
              </p>
              {result.total === 0 && (
                <p>
                  Chưa có sản phẩm khớp. Thử đổi từ khóa hoặc tự điều chỉnh bộ
                  lọc.
                </p>
              )}
              <div
                className="product-grid"
                onClick={(event) => {
                  if ((event.target as HTMLElement).closest("a")) close();
                }}
              >
                {result.items.map((row, index) => (
                  <ProductCard
                    key={row.product.id}
                    product={row.product}
                    eager={index < 4}
                  />
                ))}
              </div>
              {result.total > result.page_size && (
                <nav aria-label="Trang kết quả tại chỗ">
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy || result.page <= 1}
                    onClick={() => {
                      if (last.current)
                        void find(last.current, result.page - 1);
                    }}
                  >
                    Trang trước
                  </Button>
                  <span>
                    {result.page} / {Math.ceil(result.total / result.page_size)}
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={
                      busy || result.page * result.page_size >= result.total
                    }
                    onClick={() => {
                      if (last.current)
                        void find(last.current, result.page + 1);
                    }}
                  >
                    Trang sau
                  </Button>
                </nav>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
