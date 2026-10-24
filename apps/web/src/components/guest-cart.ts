"use client";
import { useSyncExternalStore } from "react";
import { mutate } from "@/lib/commerce";
let accountActive = false;
let pending: Promise<unknown> = Promise.resolve();
export function setCartAccount(active: boolean) {
  accountActive = active;
}
export function isCartAccount() {
  return accountActive;
}
export type CartLine = { id: string; quantity: number };
const listeners = new Set<() => void>();
export function readCart(): CartLine[] {
  try {
    const value = document.cookie
      .split("; ")
      .find((c) => c.startsWith("hm_cart="))
      ?.slice(8);
    const decoded = decodeURIComponent(value || "[]");
    const rows = JSON.parse(
      decoded === "@local"
        ? localStorage.getItem("hm_cart_large") || "[]"
        : decoded,
    );
    return Array.isArray(rows)
      ? rows
          .filter(
            (p: CartLine) =>
              typeof p.id === "string" &&
              Number.isInteger(p.quantity) &&
              p.quantity > 0 &&
              p.quantity <= 99,
          )
          .slice(0, 50)
      : [];
  } catch {
    return [];
  }
}
export function writeCart(items: CartLine[]) {
  const serialized = JSON.stringify(items);
  const encoded = encodeURIComponent(serialized);
  if (encoded.length > 3600) localStorage.setItem("hm_cart_large", serialized);
  else localStorage.removeItem("hm_cart_large");
  document.cookie = `hm_cart=${encoded.length > 3600 ? "%40local" : encoded}; Path=/; SameSite=Lax; Max-Age=2592000${location.protocol === "https:" ? "; Secure" : ""}`;
  listeners.forEach((listener) => listener());
  if (accountActive)
    pending = pending
      .catch(() => {})
      .then(() =>
        mutate(
          "/cart",
          {
            items: items.map((r) => ({
              product_id: r.id,
              quantity: r.quantity,
            })),
          },
          "PUT",
        ),
      )
      .catch(() => {
        window.dispatchEvent(new CustomEvent("hm-cart-sync-error"));
      });
}
function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
export function useCart() {
  const snapshot = useSyncExternalStore(
    subscribe,
    () => JSON.stringify(readCart()),
    () => "[]",
  );
  return JSON.parse(snapshot) as CartLine[];
}
