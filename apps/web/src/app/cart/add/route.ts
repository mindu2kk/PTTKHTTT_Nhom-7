import { NextRequest, NextResponse } from "next/server";
import { serverApi } from "@/lib/server-api";
import type { Product } from "@/lib/api";
import type { CartLine } from "@/components/guest-cart";
import { sameOrigin } from "@/lib/request-origin";
import { boundedBody, BodyReadError } from "@/lib/request-body";
export async function POST(request: NextRequest) {
  if (!sameOrigin(request))
    return new Response("Yêu cầu không hợp lệ.", { status: 403 });
  if (
    !request.headers
      .get("content-type")
      ?.startsWith("application/x-www-form-urlencoded")
  )
    return new Response("Biểu mẫu không hợp lệ.", { status: 415 });
  let bytes: Uint8Array;
  try {
    bytes = await boundedBody(request, 16384);
  } catch (error) {
    if (error instanceof BodyReadError)
      return new Response(error.message, { status: error.status });
    return new Response("Chưa đọc được biểu mẫu. Vui lòng thử lại.", {
      status: 400,
    });
  }
  const form = new URLSearchParams(new TextDecoder().decode(bytes));
  const id = String(form.get("id") || "");
  const quantity = Number(form.get("quantity"));
  const product_size_id = Number(form.get("product_size_id"));
  if (
    !/^[a-zA-Z0-9_-]{1,80}$/.test(id) ||
    !Number.isSafeInteger(product_size_id) ||
    product_size_id < 1 ||
    !Number.isInteger(quantity) ||
    quantity < 1 ||
    quantity > 99
  )
    return new Response("Số lượng không hợp lệ.", { status: 422 });
  try {
    const product = await serverApi<Product>(`/products/${id}`);
    const size = product.sizes.find((s) => s.id === product_size_id);
    if (!size) return new Response("Size không hợp lệ.", { status: 422 });
    const stored = request.cookies.get("hm_cart")?.value || "[]";
    if (stored === "@local")
      return new Response(
        "Giỏ lớn đang được lưu trong trình duyệt. Hãy bật JavaScript để tiếp tục.",
        { status: 409 },
      );
    const parsed: unknown = JSON.parse(stored);
    if (
      !Array.isArray(parsed) ||
      parsed.length > 50 ||
      parsed.some(
        (row) =>
          !row ||
          typeof row !== "object" ||
          typeof row.id !== "string" ||
          !/^[a-zA-Z0-9_-]{1,80}$/.test(row.id) ||
          !Number.isInteger(row.quantity) ||
          row.quantity < 1 ||
          row.quantity > 99,
      ) ||
      new Set(
        parsed.map((row) => `${row.id}-${row.product_size_id ?? "legacy"}`),
      ).size !== parsed.length
    )
      return new Response("Giỏ hàng không hợp lệ. Hãy kiểm tra lại giỏ hàng.", {
        status: 422,
      });
    const cart: CartLine[] = parsed;
    const old = cart.find(
      (p) => p.id === id && p.product_size_id === product_size_id,
    );
    if (
      (!old && cart.length >= 50) ||
      quantity + (old?.quantity || 0) > 99 ||
      quantity + (old?.quantity || 0) >
        Math.min(product.available_quantity, Number(size.available_quantity))
    )
      return new Response("Số lượng vượt quá tồn kho.", { status: 409 });
    const response = NextResponse.redirect(
      new URL("/cart", request.headers.get("origin")!),
      303,
    );
    response.cookies.set(
      "hm_cart",
      JSON.stringify(
        [
          ...cart.filter(
            (p) => !(p.id === id && p.product_size_id === product_size_id),
          ),
          { id, product_size_id, quantity: quantity + (old?.quantity || 0) },
        ].slice(0, 50),
      ),
      { path: "/", sameSite: "lax", maxAge: 2592000 },
    );
    return response;
  } catch {
    return new Response("Chưa thêm được vào giỏ. Vui lòng thử lại.", {
      status: 503,
    });
  }
}
