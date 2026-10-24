import "server-only";

export class BodyReadError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

// Bound both bytes and elapsed time before buffering a chunked request in the BFF.
export async function boundedBody(
  request: Request,
  limit: number,
): Promise<Uint8Array> {
  if (Number(request.headers.get("content-length") || 0) > limit)
    throw new BodyReadError(413, "Dữ liệu vượt quá dung lượng cho phép.");
  if (!request.body) return new Uint8Array();
  const reader = request.body.getReader();
  let timer: ReturnType<typeof setTimeout> | undefined;
  const deadline = new Promise<never>((_, reject) => {
    timer = setTimeout(
      () =>
        reject(
          new BodyReadError(
            408,
            "Tải dữ liệu quá thời gian. Vui lòng thử lại.",
          ),
        ),
      15000,
    );
  });
  const read = async () => {
    const chunks: Uint8Array[] = [];
    let size = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.length;
      if (size > limit)
        throw new BodyReadError(413, "Dữ liệu vượt quá dung lượng cho phép.");
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) {
      bytes.set(chunk, offset);
      offset += chunk.length;
    }
    return bytes;
  };
  try {
    return await Promise.race([read(), deadline]);
  } catch (error) {
    void reader.cancel().catch(() => {});
    throw error;
  } finally {
    clearTimeout(timer);
    reader.releaseLock();
  }
}
