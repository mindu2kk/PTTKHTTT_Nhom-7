"use client";
import { useSyncExternalStore, type ReactNode } from "react";
import { SlidersHorizontal } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetTrigger,
} from "@/components/ui/sheet";
const subscribe = (callback: () => void) => {
  const query = window.matchMedia("(max-width: 768px)");
  query.addEventListener("change", callback);
  return () => query.removeEventListener("change", callback);
};
export function FilterPanel({ children }: { children: ReactNode }) {
  const mobile = useSyncExternalStore(
    subscribe,
    () => window.matchMedia("(max-width: 768px)").matches,
    () => false,
  );
  if (!mobile) return <aside className="desktop-filters">{children}</aside>;
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="outline" className="mobile-filter-trigger">
          <SlidersHorizontal aria-hidden="true" />
          Bộ lọc sản phẩm
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="filter-drawer">
        <SheetHeader>
          <SheetTitle>Bộ lọc sản phẩm</SheetTitle>
          <SheetDescription>
            Chọn điều kiện rồi bấm Áp dụng bộ lọc.
          </SheetDescription>
        </SheetHeader>
        {children}
      </SheetContent>
    </Sheet>
  );
}
