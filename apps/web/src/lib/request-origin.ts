import "server-only";
export function trustedHost(request: Request) {
  const port = process.env.PUBLIC_WEB_PORT || "3000";
  return [`localhost:${port}`, `127.0.0.1:${port}`].includes(
    (request.headers.get("host") || "").toLowerCase(),
  );
}
export function sameOrigin(request: Request) {
  if (!trustedHost(request)) return false;
  try {
    const origin = new URL(request.headers.get("origin") || "");
    return (
      origin.host.toLowerCase() ===
        request.headers.get("host")?.toLowerCase() &&
      ["http:", "https:"].includes(origin.protocol)
    );
  } catch {
    return false;
  }
}
