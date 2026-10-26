import Link from "next/link";
export default function Help() {
  return (
    <div className="wrap section-block prose-page">
      <h1>Trợ giúp & quyền riêng tư</h1>
      <section>
        <h2>Đặt thử trên Hoodoo</h2>
        <p>
          Giá và hạn mức đặt thử là dữ liệu mô phỏng, không phải tồn kho hay giá
          bán trực tiếp của shop nguồn. Chọn sản phẩm, thêm giỏ, đăng nhập rồi đặt thử bằng
          COD hoặc thanh toán mô phỏng. Không nhập số thẻ, không có khoản thu
          hay dịch vụ giao hàng thật.
        </p>
        <Link href="/account/orders">Xem đơn hàng của tôi</Link>
      </section>
      <section>
        <h2>Tìm theo văn bản, giọng nói hoặc ảnh</h2>
        <p>
          Nhận giọng có thể sai. Kiểm tra và sửa bản chép lời trước khi tìm.
          Chrome trên thiết bị là tính năng thử nghiệm; nếu không hỗ trợ, dùng
          tệp âm thanh hoặc nhập văn bản. Ảnh nhận JPEG, PNG, WebP tối đa 5 MB;
          âm thanh tối đa 15 giây và 2 MB.
        </p>
        <Link href="/search">Mở tìm kiếm</Link>
      </section>
      <section>
        <h2>Dữ liệu của bạn</h2>
        <p>
          Ảnh và âm thanh tải lên chỉ được xử lý tạm, không lưu vào catalog.
          Lịch sử tìm kiếm mặc định tắt; khi bật, tối đa 100 câu trong 7 ngày.
          Đơn hàng chỉ chủ tài khoản được xem. Hồ sơ và phiên được lưu cục bộ
          cho bài thực hành.
        </p>
        <Link href="/account/history">Quản lý lịch sử</Link>
      </section>
      <section>
        <h2>Nguồn và giới hạn</h2>
        <p>
          Màu, chất liệu hoặc phiên bản thiếu được ghi rõ; không có đánh giá,
          lượt bán, giảm giá hay cam kết giao hàng được tạo giả.
        </p>
        <Link href="/sources">Xem quyền dữ liệu và ảnh</Link>
      </section>
    </div>
  );
}
