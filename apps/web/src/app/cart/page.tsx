import { CartView } from "@/components/cart-view";
export default function Cart() {
  return (
    <div className="wrap section-block">
      <h1>Giỏ hàng</h1>
      <p className="lead">Chọn số lượng và kiểm tra sản phẩm của bạn.</p>
      <CartView />
    </div>
  );
}
