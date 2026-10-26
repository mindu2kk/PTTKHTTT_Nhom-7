"use client";
import { useState } from "react";
import { ProductPhoto } from "@/components/product-photo";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
export function ProductGallery({
  images,
}: {
  images: { url: string; alt: string }[];
}) {
  const [index, setIndex] = useState(0);
  const image = images[index];
  return (
    <div className="product-gallery">
      <Dialog>
        <DialogTrigger asChild>
          <button className="gallery-main" aria-label="Phóng to ảnh sản phẩm">
            <ProductPhoto src={image.url} alt={image.alt} large eager />
          </button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-3xl">
          <DialogTitle>Ảnh sản phẩm</DialogTitle>
          <DialogDescription>
            Ảnh sản phẩm từ nguồn đã duyệt.
          </DialogDescription>
          <img
            className="zoom-photo"
            src={image.url}
            alt={image.alt}
            width={960}
            height={960}
          />
        </DialogContent>
      </Dialog>
      <div className="gallery-thumbnails">
        {images.map((item, n) => (
          <button
            key={item.url}
            onClick={() => setIndex(n)}
            aria-pressed={index === n}
            aria-label={`Xem ảnh ${n + 1}`}
          >
            <ProductPhoto src={item.url} alt={item.alt} />
          </button>
        ))}
      </div>
      <p className="gallery-hint">Chọn ảnh thu nhỏ · Bấm ảnh lớn để phóng to</p>
    </div>
  );
}
