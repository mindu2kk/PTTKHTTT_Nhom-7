"use client";
import Link from "next/link";
import { Menu } from "lucide-react";
import type { Category } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetClose,
} from "@/components/ui/sheet";

export function CategoryMenu({ categories }: { categories: Category[] }) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button variant="ghost">
          <Menu data-icon="inline-start" />
          Danh mục
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="category-menu">
        <SheetHeader>
          <SheetTitle>Danh mục sản phẩm</SheetTitle>
          <SheetDescription>
            Khám phá các sản phẩm đang công khai.
          </SheetDescription>
        </SheetHeader>
        <nav aria-label="Tất cả danh mục" className="category-menu-links">
          <SheetClose asChild>
            <Link href="/products">Tất cả sản phẩm</Link>
          </SheetClose>
          {categories
            .filter((c) => c.level === 0)
            .map((root) => (
              <section key={root.id}>
                <SheetClose asChild>
                  <Link
                    className="category-root"
                    href={`/products?category=${root.id}`}
                  >
                    {root.name_vi}
                  </Link>
                </SheetClose>
                {categories
                  .filter((c) => c.parent_id === root.id)
                  .map((group) => (
                    <div key={group.id}>
                      <SheetClose asChild>
                        <Link href={`/products?category=${group.id}`}>
                          {group.name_vi}
                        </Link>
                      </SheetClose>
                      {categories
                        .filter((c) => c.parent_id === group.id)
                        .map((leaf) => (
                          <SheetClose asChild key={leaf.id}>
                            <Link
                              className="category-leaf"
                              href={`/products?category=${leaf.id}`}
                            >
                              {leaf.name_vi}
                            </Link>
                          </SheetClose>
                        ))}
                    </div>
                  ))}
              </section>
            ))}
        </nav>
      </SheetContent>
    </Sheet>
  );
}
