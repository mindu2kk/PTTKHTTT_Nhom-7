import Link from "next/link";
import { Product, money } from "@/lib/api";
import { ProductPhoto } from "@/components/product-photo";
export function ProductCard({
  product,
  eager = false,
}: {
  product: Product;
  eager?: boolean;
}) {
  return (
    <article className="product-card">
      <Link href={`/products/${product.slug}`} className="product-picture">
        <ProductPhoto
          src={product.image_url}
          alt={product.image_alt}
          eager={eager}
        />
        {product.available_quantity === 0 && (
          <span className="stock-label">Tạm hết hàng</span>
        )}
      </Link>
      <div className="product-meta">
        <h3>
          <Link href={`/products/${product.slug}`}>{product.name_vi}</Link>
        </h3>
        <strong>{money(product.price_vnd)}</strong>
        <p>{product.brand || product.category_name}</p>
      </div>
    </article>
  );
}
