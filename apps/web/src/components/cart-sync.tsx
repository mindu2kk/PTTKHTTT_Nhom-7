"use client";
import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
import {
  readCart,
  setCartAccount,
  writeCart,
  isCartAccount,
} from "@/components/guest-cart";
export function CartSync() {
  const pathname = usePathname();
  useEffect(() => {
    let live = true;
    api("/auth/me")
      .then(async () => {
        if (!live) return;
        const wasActive = isCartAccount();
        setCartAccount(true);
        if (!wasActive && !readCart().length) {
          const cart = await api<{
            items: {
              product_id: string;
              product_size_id: number;
              quantity: number;
            }[];
          }>("/cart");
          if (live && cart.items.length)
            writeCart(
              cart.items.map((i) => ({
                id: i.product_id,
                product_size_id: i.product_size_id,
                quantity: i.quantity,
              })),
            );
        }
      })
      .catch(() => {
        if (live) setCartAccount(false);
      });
    return () => {
      live = false;
    };
  }, [pathname]);
  return null;
}
