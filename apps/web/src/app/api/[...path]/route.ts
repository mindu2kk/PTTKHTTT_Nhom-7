import { NextRequest } from "next/server";
import { backend } from "@/lib/server-api";
import { trustedHost, sameOrigin } from "@/lib/request-origin";
import { boundedBody, BodyReadError } from "@/lib/request-body";
async function proxy(
  request: NextRequest,
  context: { params: Promise<{ path: string[] }> },
) {
  const { path } = await context.params;
  if (path[0] !== "v1")
    return Response.json(
      { detail: "Không tìm thấy đường dẫn." },
      { status: 404 },
    );
  if (!trustedHost(request))
    return Response.json(
      { detail: "Địa chỉ truy cập không hợp lệ." },
      { status: 421 },
    );
  if (request.method !== "GET" && !sameOrigin(request))
    return Response.json({ detail: "Yêu cầu không hợp lệ." }, { status: 403 });
  if (Number(request.headers.get("content-length") || 0) > 6 * 1024 * 1024)
    return Response.json(
      { detail: "Tệp vượt quá dung lượng cho phép." },
      { status: 413 },
    );
  try {
    let body: Uint8Array | undefined;
    if (request.method !== "GET" && request.body) {
      const limit = path.includes("image")
        ? 6 * 1024 * 1024
        : path.includes("voice")
          ? 3 * 1024 * 1024
          : 128 * 1024;
      body = await boundedBody(request, limit);
    }
    const headers = new Headers();
    for (const name of [
      "content-type",
      "cookie",
      "x-csrf-token",
      "idempotency-key",
      "origin",
    ]) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    const response = await fetch(
      `${backend()}/api/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`,
      {
        method: request.method,
        headers,
        body: body as BodyInit | undefined,
        cache: "no-store",
        signal: AbortSignal.timeout(65000),
      },
    );
    const outgoing = new Headers({
      "Content-Type":
        response.headers.get("content-type") || "application/json",
      "Cache-Control": "no-store",
    });
    for (const cookie of response.headers.getSetCookie())
      outgoing.append("Set-Cookie", cookie);
    return new Response(response.body, {
      status: response.status,
      headers: outgoing,
    });
  } catch (error) {
    if (error instanceof BodyReadError)
      return Response.json({ detail: error.message }, { status: error.status });
    return Response.json(
      { detail: "Không kết nối được dịch vụ. Vui lòng thử lại." },
      { status: 503 },
    );
  }
}
export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const PUT = proxy;
