export default function Sources() {
  return (
    <div className="wrap section-block prose-page">
      <h1>Nguồn dữ liệu và ảnh</h1>
      <p>
        Banner trang chủ là ảnh minh họa do AI tạo riêng cho HoodooMart, không
        phải ảnh của một sản phẩm trong catalog.
      </p>
      <section>
        <h2>Amazon Berkeley Objects (ABO)</h2>
        <p>
          Dữ liệu sản phẩm và ảnh: © Amazon.com. Bộ dữ liệu: Matthieu
          Guillaumin, Thomas Dideriksen, Kenan Deng, Himanshu Arora, Jasmine
          Collins và Jitendra Malik.
        </p>
        <p>
          Giấy phép{" "}
          <a
            href="https://creativecommons.org/licenses/by/4.0/"
            rel="noreferrer"
          >
            Creative Commons Attribution 4.0
          </a>
          , được kiểm tra ngày 22/10/2026 trên{" "}
          <a
            href="https://registry.opendata.aws/amazon-berkeley-objects/"
            rel="noreferrer"
          >
            AWS Open Data Registry
          </a>{" "}
          và{" "}
          <a
            href="https://amazon-berkeley-objects.s3.amazonaws.com/README.md"
            rel="noreferrer"
          >
            README chính thức
          </a>
          .
        </p>
        <p>
          HoodooMart chọn một phần metadata của listings_0 (ETag
          49304dd0edc3aa3d4cb19231927732fc). Mỗi ảnh liên kết bằng
          main_image_id/other_image_id của chính sản phẩm, được chuyển WebP, thu
          nhỏ và bỏ metadata. Tên và mô tả tiếng Việt được ánh xạ từ loại, nhãn
          hiệu và mã mẫu; tên gốc được giữ ở trang chi tiết. Không dùng ảnh từ
          nguồn không rõ quyền.
        </p>
        <p>
          Giá và hạn mức đặt thử là cấu hình riêng của HoodooMart, không phải
          giá hay tồn kho của nguồn. Không có bảo trợ, xác nhận thương nhân hay
          quyền nhãn hiệu được suy ra từ giấy phép. Dữ liệu cung cấp nguyên
          trạng, không bảo đảm còn được bán.
        </p>
      </section>
      <section>
        <h2>Dữ liệu bài học</h2>
        <p>
          Fixture M7 do dự án tạo, CC0, được giữ riêng khỏi catalog ảnh thật.
          Không nhận là dữ liệu Tiki hoặc Shopee. Tìm kiếm và checkout trong ứng
          dụng này phục vụ trải nghiệm cục bộ.
        </p>
      </section>
    </div>
  );
}
