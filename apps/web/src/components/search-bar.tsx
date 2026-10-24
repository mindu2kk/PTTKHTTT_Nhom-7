"use client";
import { Camera, Mic, Search } from "lucide-react";
import { openSearch, SEARCH_QUERY } from "@/lib/unified-search";
import { clipboardImage } from "@/lib/search-input";
import { useEffect, useState, useId } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
export function SearchBar({
  initial = "",
  compact = false,
  header = false,
}: {
  initial?: string;
  compact?: boolean;
  header?: boolean;
}) {
  const [query, setQuery] = useState(initial);
  const [suggestions, setSuggestions] = useState<{
    query: string;
    values: string[];
  }>({ query: "", values: [] });
  const listId = useId();
  const inputId = useId();
  useEffect(() => {
    const update = (event: Event) => {
      const value = (event as CustomEvent<unknown>).detail;
      if (typeof value === "string") setQuery(value.slice(0, 300));
    };
    window.addEventListener(SEARCH_QUERY, update);
    return () => window.removeEventListener(SEARCH_QUERY, update);
  }, []);
  useEffect(() => {
    if (query.trim().length < 2 || query.trim().length > 100) return;
    const controller = new AbortController();
    const timer = setTimeout(() => {
      api<{ suggestions: string[] }>(
        `/search/suggestions?q=${encodeURIComponent(query)}`,
        { signal: controller.signal },
      )
        .then((data) => {
          if (!controller.signal.aborted)
            setSuggestions({ query, values: data.suggestions });
        })
        .catch(() => {});
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [query]);
  return (
    <section
      className={
        header
          ? "search-panel header-search"
          : compact
            ? "search-panel compact"
            : "search-panel"
      }
      aria-label="Tìm sản phẩm"
    >
      <form
        action="/search"
        method="get"
        className="search-form"
        onSubmit={(event) => {
          event.preventDefault();
          if (query.trim()) openSearch({ mode: "text", query });
        }}
        onPaste={(event) => {
          const image = clipboardImage(event.clipboardData.items);
          if (image) {
            event.preventDefault();
            openSearch({ mode: "image", query, file: image });
          }
        }}
      >
        <Search aria-hidden="true" />
        <label className="sr-only" htmlFor={inputId}>
          {header ? "Tìm nhanh sản phẩm" : "Bạn đang tìm gì?"}
        </label>
        <input
          id={inputId}
          name="q"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          list={listId}
          placeholder="Tìm sản phẩm, thương hiệu hoặc mô tả điều bạn cần"
          maxLength={300}
          required
        />
        <datalist id={listId}>
          {query.length >= 2 &&
            suggestions.query === query &&
            suggestions.values.map((value) => (
              <option key={value} value={value} />
            ))}
        </datalist>
        {header && (
          <>
            <button
              type="button"
              className="search-tool"
              onClick={() => openSearch({ mode: "voice", query })}
              aria-label="Tìm bằng giọng nói"
            >
              <Mic aria-hidden="true" />
            </button>
            <button
              type="button"
              className="search-tool"
              onClick={() => openSearch({ mode: "image", query })}
              aria-label="Tìm bằng hình ảnh"
            >
              <Camera aria-hidden="true" />
            </button>
          </>
        )}
        <Button type="submit" aria-label={header ? "Tìm nhanh" : "Tìm kiếm"}>
          {header ? <Search aria-hidden="true" /> : "Tìm kiếm"}
        </Button>
      </form>
      {!header && (
        <div className="input-modes">
          <span>Tìm theo cách của bạn</span>
          <button
            type="button"
            onClick={() => openSearch({ mode: "voice", query })}
          >
            <Mic aria-hidden="true" />
            Giọng nói
          </button>
          <button
            type="button"
            onClick={() => openSearch({ mode: "image", query })}
          >
            <Camera aria-hidden="true" />
            Hình ảnh
          </button>
        </div>
      )}
    </section>
  );
}
