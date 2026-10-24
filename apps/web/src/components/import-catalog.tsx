"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { mutate } from "@/lib/commerce";
type Preview = {
  rows: number;
  errors: { row: number; field: string; message: string }[];
  publish_status: string;
};
export function ImportCatalog() {
  const [source, setSource] = useState("");
  const [preview, setPreview] = useState<Preview>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();
  async function run(commit: boolean) {
    setBusy(true);
    setError("");
    try {
      const records = JSON.parse(source);
      if (!Array.isArray(records) || records.length > 20)
        throw new Error("Nhập một mảng JSON, tối đa 20 sản phẩm.");
      const result = await mutate<Preview>(
        commit ? "/manage/imports" : "/manage/imports/preview",
        { records },
      );
      if (commit) {
        setSource("");
        setPreview(undefined);
        setError(
          "Đã nhập bản nháp. Kiểm tra từng sản phẩm rồi duyệt xuất bản.",
        );
        router.refresh();
      } else setPreview(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <details className="manage-create">
      <summary>Nhập danh mục mô phỏng theo đợt</summary>
      <div className="account-form">
        <p>
          Dán mảng JSON tối đa 20 sản phẩm theo mẫu trong RUNBOOK. Chỉ dùng dữ
          liệu bạn tạo và có quyền dùng theo CC0; ảnh phải thuộc thư viện minh
          họa đã duyệt.
        </p>
        <label>
          Dữ liệu JSON
          <textarea
            rows={8}
            maxLength={100000}
            value={source}
            onChange={(e) => {
              setSource(e.target.value);
              setPreview(undefined);
            }}
          />
        </label>
        <Button
          variant="outline"
          disabled={busy || !source.trim()}
          onClick={() => run(false)}
        >
          Xem trước và kiểm tra
        </Button>
        {preview && (
          <div>
            <p>
              {preview.rows} dòng · {preview.errors.length} lỗi. Sản phẩm được
              nhập ở trạng thái bản nháp.
            </p>
            {preview.errors.map((e, i) => (
              <p key={i}>
                Dòng {e.row} · {e.field}: {e.message}
              </p>
            ))}
            <Button
              disabled={busy || preview.errors.length > 0}
              onClick={() => run(true)}
            >
              Xác nhận nhập bản nháp
            </Button>
          </div>
        )}
        {error && <p role="status">{error}</p>}
      </div>
    </details>
  );
}
