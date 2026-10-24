import Link from "next/link";
import { ArrowRight, Shirt, Headphones, Lamp, Footprints } from "lucide-react";
import { serverApi } from "@/lib/server-api";
import type { Category, ProductPage } from "@/lib/api";
import { ProductCard } from "@/components/product-card";
import { MarketplaceBanner } from "@/components/marketplace-banner";

const ROOT_ORDER = ["thoi-trang-nam", "thoi-trang-nu", "dien-tu", "gia-dung"];
const CATEGORY_ICONS = {
  "thoi-trang-nam": Shirt,
  "thoi-trang-nu": Footprints,
  "dien-tu": Headphones,
  "gia-dung": Lamp,
};

export default async function Home() {
  const [categories, products] = await Promise.all([
    serverApi<Category[]>("/categories"),
    serverApi<ProductPage>("/products?page_size=24"),
  ]);
  const roots = categories
    .filter((c) => c.level === 0)
    .sort((a, b) => ROOT_ORDER.indexOf(a.id) - ROOT_ORDER.indexOf(b.id));
  return (
    <>
      <h1 className="sr-only">HoodooMart</h1>
      <MarketplaceBanner />
      <nav className="wrap home-category-links" aria-label="Khám phá danh mục">
        {roots.map((category) => {
          const Icon =
            CATEGORY_ICONS[category.id as keyof typeof CATEGORY_ICONS] || Shirt;
          return (
            <Link key={category.id} href={`/products?category=${category.id}`}>
              <span>
                <Icon aria-hidden="true" />
              </span>
              {category.name_vi}
            </Link>
          );
        })}
      </nav>
      <section
        className="wrap home-products"
        aria-labelledby="home-products-title"
      >
        <div className="section-heading">
          <h2 id="home-products-title">Khám phá sản phẩm</h2>
          <Link href="/products">
            Xem tất cả <ArrowRight aria-hidden="true" />
          </Link>
        </div>
        <div className="product-grid home-grid">
          {products.items.map((product, index) => (
            <ProductCard key={product.id} product={product} eager={index < 6} />
          ))}
        </div>
      </section>
    </>
  );
}
