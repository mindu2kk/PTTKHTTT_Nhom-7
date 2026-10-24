import type { components } from "@/lib/schema";
export type Product = components["schemas"]["ProductResponse"];
export type Category = components["schemas"]["CategoryResponse"];
export type ProductPage = components["schemas"]["ProductPage"];
export class ApiClientError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export const money = (value: number) =>
  new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (typeof document !== "undefined") {
    const token = document.cookie
      .split("; ")
      .find((c) => c.startsWith("hm_csrf="))
      ?.split("=")[1];
    if (token) headers.set("X-CSRF-Token", decodeURIComponent(token));
  }
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers,
    credentials: "same-origin",
  });
  const data = await response.json();
  if (!response.ok)
    throw new ApiClientError(
      response.status,
      data.detail || "Dịch vụ tạm thời chưa sẵn sàng. Vui lòng thử lại.",
    );
  return data as T;
}
