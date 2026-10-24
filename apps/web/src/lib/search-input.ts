export function imageInputError(file: Pick<File, "type" | "size">): string {
  if (!["image/jpeg", "image/png", "image/webp"].includes(file.type))
    return "Chỉ nhận ảnh JPEG, PNG hoặc WebP.";
  if (file.size === 0 || file.size > 5 * 1024 * 1024)
    return "Ảnh cần có nội dung và không quá 5 MB.";
  return "";
}

export function searchBudget(value: string): string {
  return /^\d+$/.test(value) && Number(value) <= 1e12 ? value : "";
}

export function clipboardImage(
  items: Iterable<Pick<DataTransferItem, "kind" | "type" | "getAsFile">>,
): File | null {
  for (const item of items) {
    if (item.kind === "file" && item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) return file;
    }
  }
  return null;
}
