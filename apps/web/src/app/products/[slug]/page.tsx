import Link from "next/link";
import { notFound } from "next/navigation";
import { serverApi } from "@/lib/server-api";
import { money, type Product } from "@/lib/api";
import { AddToCart } from "@/components/add-to-cart";
import { ProductGallery } from "@/components/product-gallery";
import { ProductCard } from "@/components/product-card";
import type { ProductPage } from "@/lib/api";
export default async function Detail({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  let product: Product;
  try {
    product = await serverApi<Product>(`/products/${encodeURIComponent(slug)}`);
  } catch (error) {
    if (error instanceof Error && error.message === "Không tìm thấy sản phẩm.")
      notFound();
    throw error;
  }
  const data = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name_vi,
    description: product.description_vi,
    sku: product.id,
    // Dataset demo offers must not advertise merchant inventory in structured data.
    offers:
      product.data_profile === "real_demo"
        ? undefined
        : {
            "@type": "Offer",
            priceCurrency: "VND",
            price: product.price_vnd,
            availability:
              product.available_quantity > 0
                ? "https://schema.org/InStock"
                : "https://schema.org/OutOfStock",
          },
    additionalProperty:
      product.data_profile === "real_demo"
        ? [
            {
              "@type": "PropertyValue",
              name: "Giá đặt thử mô phỏng",
              value: product.price_vnd,
              unitText: "VND",
            },
          ]
        : undefined,
  };
  const related = await serverApi<ProductPage>(
    `/products?category=${encodeURIComponent(product.category_id)}&page_size=6`,
  );
  const photos = product.images?.length
    ? product.images.map((i) => ({ url: String(i.url), alt: String(i.alt) }))
    : [{ url: product.image_url, alt: product.image_alt }];
  return (
    <div className="wrap section-block">
      <nav className="breadcrumbs" aria-label="Đường dẫn">
        <Link href="/">Trang chủ</Link>
        <span>/</span>
        <Link href={`/products?category=${product.category_id}`}>
          {product.category_name}
        </Link>
      </nav>
      <div className="product-detail">
        <ProductGallery images={photos} />
        <section>
          <p className="category-name">{product.category_name}</p>
          <h1>{product.name_vi}</h1>
          <p className="fine-print">
            Mã sản phẩm: {product.id.replace(/^rhodi-/, "hoodoo-")}
          </p>
          <p className="detail-price">{money(product.price_vnd)}</p>
          <AddToCart product={product} />
          <p className="fine-print">
            Giá và tồn kho được kiểm tra lại khi đặt hàng. Đơn hàng trong bản
            demo không phát sinh thanh toán thật.
          </p>
        </section>
      </div>
      <section className="section-block">
        <div className="section-heading">
          <h2>Sản phẩm liên quan</h2>
          <Link href={`/products?category=${product.category_id}`}>
            Xem danh mục
          </Link>
        </div>
        <div className="product-grid">
          {related.items
            .filter((p) => p.id !== product.id)
            .slice(0, 6)
            .map((p) => (
              <ProductCard product={p} key={p.id} />
            ))}
        </div>
        <p className="fine-print">
          Ảnh và dữ liệu:{" "}
          <Link href="/sources">nguồn, giấy phép và thay đổi</Link>. Đơn đặt thử
          không phát sinh thanh toán thật.
        </p>
      </section>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify(data).replace(/</g, "\\u003c"),
        }}
      />
    </div>
  );
}
