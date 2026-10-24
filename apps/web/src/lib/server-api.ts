import "server-only";
import { cookies } from "next/headers";
export const backend = () =>
  process.env.API_INTERNAL_URL || "http://127.0.0.1:8000";
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function serverApi<T>(path: string): Promise<T> {
  const jar = await cookies();
  const response = await fetch(`${backend()}/api/v1${path}`, {
    cache: "no-store",
    headers: { cookie: jar.toString() },
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok)
    throw new ApiError(
      response.status,
      response.status === 404
        ? "Không tìm thấy sản phẩm."
        : "Danh mục tạm thời chưa sẵn sàng. Vui lòng thử lại.",
    );
  return response.json() as Promise<T>;
}
