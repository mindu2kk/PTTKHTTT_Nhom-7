import { Skeleton } from "@/components/ui/skeleton";
export function CatalogSkeleton() {
  return (
    <div
      className="wrap section-block"
      role="status"
      aria-label="Đang tải sản phẩm"
    >
      <Skeleton className="h-9 w-64 mb-6" />
      <div className="product-grid">
        {Array.from({ length: 12 }, (_, i) => (
          <Skeleton key={i} className="h-72 w-full" />
        ))}
      </div>
    </div>
  );
}
