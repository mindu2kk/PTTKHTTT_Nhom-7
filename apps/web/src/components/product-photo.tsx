"use client";
import Image from "next/image";
import { ImageOff } from "lucide-react";
import { useState } from "react";

export function ProductPhoto({
  src,
  alt,
  eager = false,
  large = false,
}: {
  src: string;
  alt: string;
  eager?: boolean;
  large?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  if (failed)
    return (
      <span
        className="photo-unavailable"
        role="img"
        aria-label="Ảnh sản phẩm chưa khả dụng"
      >
        <ImageOff aria-hidden="true" />
        <span>Ảnh chưa khả dụng</span>
      </span>
    );
  const photo =
    src.startsWith("/media/catalog/") && !large
      ? src.replace(/\.webp$/, "-320.webp")
      : src;
  return (
    <Image
      src={photo}
      alt={alt}
      width={large ? 960 : 320}
      height={large ? 960 : 320}
      sizes={
        large
          ? "(max-width: 768px) 90vw, 520px"
          : "(max-width: 600px) 46vw, (max-width: 1000px) 28vw, 220px"
      }
      unoptimized={true}
      loading={eager ? "eager" : "lazy"}
      onError={() => setFailed(true)}
    />
  );
}
