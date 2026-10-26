"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowRight, ChevronLeft, ChevronRight, Pause, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";

const slides = [
  {
    image: "main1.jpg",
    alt: "Người mẫu mặc sơ mi đỏ, cầm ván trượt ngoài trời",
    title: "Tự do thể hiện.",
    description: "Trang phục đồng hành cùng nhịp sống của bạn.",
    action: "Khám phá áo",
    href: "/products?category=nam-ao",
  },
  {
    image: "main2.jpg",
    alt: "Người mẫu mặc suit đen và sơ mi trắng trong không gian tối",
    title: "Lịch lãm mỗi ngày.",
    description: "Một chiếc sơ mi. Nhiều cách tạo dấu ấn.",
    action: "Khám phá sơ mi",
    href: "/products?category=nam-ao-so-mi",
  },
  {
    image: "main3.jpg",
    alt: "Người mẫu mặc áo khoác denim, áo đen và quần màu be",
    title: "Đơn giản. Khác biệt.",
    description: "Tìm cảm hứng cho cách phối đồ của riêng bạn.",
    action: "Xem sản phẩm",
    href: "/products",
  },
];

export function MarketplaceBanner() {
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(true);
  const region = useRef<HTMLElement>(null);
  const touchStart = useRef<number | null>(null);

  useEffect(() => {
    const preference = window.matchMedia("(prefers-reduced-motion: reduce)");
    const respectPreference = () => {
      if (preference.matches) setPlaying(false);
    };
    const startup = window.setTimeout(respectPreference, 0);
    preference.addEventListener("change", respectPreference);
    return () => {
      window.clearTimeout(startup);
      preference.removeEventListener("change", respectPreference);
    };
  }, []);

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      if (document.hidden || region.current?.matches(":hover, :focus-within")) return;
      setIndex((current) => (current + 1) % slides.length);
    }, 6000);
    return () => window.clearInterval(timer);
  }, [playing]);

  function goTo(next: number) {
    setIndex((next + slides.length) % slides.length);
    setPlaying(false);
  }

  return (
    <section
      ref={region}
      className="home-campaign"
      aria-label="Giới thiệu thời trang Hoodoo"
      aria-roledescription="trình chiếu ảnh"
      onKeyDown={(event) => {
        if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
          event.preventDefault();
          goTo(index + (event.key === "ArrowRight" ? 1 : -1));
        }
      }}
      onTouchStart={(event) => { touchStart.current = event.touches[0].clientX; }}
      onTouchEnd={(event) => {
        if (touchStart.current === null) return;
        const distance = touchStart.current - event.changedTouches[0].clientX;
        if (Math.abs(distance) > 50) goTo(index + (distance > 0 ? 1 : -1));
        touchStart.current = null;
      }}
      onTouchCancel={() => { touchStart.current = null; }}
    >
      <div className="campaign-track" style={{ transform: `translateX(-${index * 100}%)` }}
        aria-live={playing ? "off" : "polite"}>
        {slides.map((slide, number) => (
          <article key={slide.image} className="campaign-slide"
            aria-label={`Ảnh ${number + 1} trên ${slides.length}`}
            aria-hidden={number !== index} inert={number !== index}>
            <div className="campaign-image">
              <Image src={`/images/campaign/menswear/${slide.image}`} alt={slide.alt}
                fill sizes="(max-width: 640px) 100vw, 64vw" unoptimized
                preload={number === 0} loading={number === 0 ? undefined : "eager"} />
            </div>
            <div className="campaign-copy">
              <p className="campaign-brand">Hoodoo · Thời trang nam</p>
              <h2>{slide.title}</h2>
              <p className="campaign-description">{slide.description}</p>
              <Link className="campaign-action" href={slide.href}>
                {slide.action} <ArrowRight aria-hidden="true" />
              </Link>
            </div>
          </article>
        ))}
      </div>
      <button className="campaign-arrow campaign-previous" aria-label="Ảnh trước"
        onClick={() => goTo(index - 1)}><ChevronLeft aria-hidden="true" /></button>
      <button className="campaign-arrow campaign-next" aria-label="Ảnh tiếp theo"
        onClick={() => goTo(index + 1)}><ChevronRight aria-hidden="true" /></button>
      <div className="campaign-pagination" aria-label="Chọn ảnh giới thiệu">
        {slides.map((slide, number) => (
          <button key={slide.image} aria-label={`Xem ảnh ${number + 1}`}
            aria-current={number === index ? "true" : undefined}
            onClick={() => goTo(number)}><span /></button>
        ))}
      </div>
      <button className="campaign-playback" onClick={() => setPlaying(!playing)}
        aria-label={playing ? "Tạm dừng chuyển ảnh" : "Bật tự chuyển ảnh"}>
        {playing ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
      </button>
    </section>
  );
}
