export default function Sources() {
  return (
    <div className="wrap section-block prose-page">
      <h1>Nguồn dữ liệu và ảnh</h1>
      <p>
        Banner trang chủ sử dụng ảnh do người vận hành cung cấp để giới thiệu
        phong cách thời trang. Đây không phải ảnh của một sản phẩm trong catalog;
        watermark và thông tin ghi công trong ảnh được giữ nguyên.
      </p>
      <section>
        <h2>Sản phẩm do quản trị viên bổ sung</h2>
        <p>Thông tin mới do quản trị viên tạo và xác nhận quyền sử dụng. Ảnh được nhập bằng URL trực tiếp từ Postimages, kiểm tra định dạng, kích thước và xác nhận quyền trước khi xuất bản. File ảnh được hiển thị từ URL gốc; không lưu vào dự án.</p>
      </section>
      <section>
        <h2>Mẫu thời trang Rhodi</h2>
        <p>
          Các sản phẩm từ bảng dữ liệu người vận hành cung cấp. Người vận hành
          đã xác nhận quyền sử dụng sản phẩm và ảnh cho web demo. Ảnh được tải
          trực tiếp từ Postimages trong trình duyệt; không lưu file ảnh vào project.
          Đây không phải tuyên bố ảnh thuộc giấy phép mở hay shop bảo trợ Hoodoo.
        </p>
        <p>Giá và số lượng chỉ dùng để đặt thử, không xác nhận tồn kho trực tiếp của shop.</p>
      </section>
      <section>
        <h2>Nguồn thử nghiệm trước đây: Amazon Berkeley Objects (ABO)</h2>
        <p>Nguồn này không áp dụng cho mẫu thời trang Rhodi ở trên.</p>
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
          Hoodoo chọn một phần metadata của listings_0 (ETag
          49304dd0edc3aa3d4cb19231927732fc). Mỗi ảnh liên kết bằng
          main_image_id/other_image_id của chính sản phẩm, được chuyển WebP, thu
          nhỏ và bỏ metadata. Tên và mô tả tiếng Việt được ánh xạ từ loại, nhãn
          hiệu và mã mẫu; tên gốc được giữ ở trang chi tiết. Không dùng ảnh từ
          nguồn không rõ quyền.
        </p>
        <p>
          Giá và hạn mức đặt thử là cấu hình riêng của Hoodoo, không phải
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
