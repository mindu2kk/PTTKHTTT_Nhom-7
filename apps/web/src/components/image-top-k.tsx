"use client";

import { useId } from "react";

export function ImageTopK({
  value,
  onChange,
  disabled,
}: {
  value: string;
  onChange: (value: string) => void;
  disabled: boolean;
}) {
  const id = useId();
  return (
    <label htmlFor={id} className="grid gap-2">
      Số sản phẩm tương đồng nhất
      <input
        id={id}
        name="top_k"
        className="h-10 w-28 rounded-md border border-input bg-background px-3"
        type="number"
        min={1}
        max={100}
        step={1}
        required
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
      />
      <span className="text-sm text-muted-foreground">
        Chọn từ 1 đến 100. Mỗi sản phẩm chỉ xuất hiện một lần.
      </span>
    </label>
  );
}
