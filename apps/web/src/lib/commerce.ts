import type { components } from "@/lib/schema";
import { api } from "@/lib/api";
export type Account = components["schemas"]["AccountResponse"];
export type Order = components["schemas"]["OrderResponse"];
export async function prepareForm() {
  if (document.cookie.split("; ").some((c) => c.startsWith("hm_csrf="))) return;
  await api("/auth/csrf");
}
export async function mutate<T>(
  path: string,
  body?: unknown,
  method = "POST",
  key?: string,
) {
  await prepareForm();
  return api<T>(path, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(key ? { "Idempotency-Key": key } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}
export const statusLabel: Record<string, string> = {
  CONFIRMED: "Đã xác nhận",
  PACKING: "Đang chuẩn bị",
  SHIPPED: "Đang giao",
  DELIVERED: "Đã giao",
  CANCELLED: "Đã hủy",
};
