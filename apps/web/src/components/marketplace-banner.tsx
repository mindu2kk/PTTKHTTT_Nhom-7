import Image from "next/image";
import Link from "next/link";

export function MarketplaceBanner() {
  return (
    <div className="wrap home-campaign">
      <Link href="/products" aria-label="Khám phá sản phẩm HoodooMart">
        <Image
          src="/images/campaign/hoodoomart-still-life-v1.png"
          alt="Minh họa bộ sưu tập với giày, tai nghe và đèn trên nền cam"
          width={2179}
          height={722}
          sizes="(max-width: 768px) 100vw, 1240px"
          preload
        />
      </Link>
    </div>
  );
}
