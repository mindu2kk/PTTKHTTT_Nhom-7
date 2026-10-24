import { AuthForm } from "@/components/account-forms";
import { notFound } from "next/navigation";
export default async function Auth({
  params,
  searchParams,
}: {
  params: Promise<{ mode: string }>;
  searchParams: Promise<{ next?: string }>;
}) {
  const { mode } = await params;
  if (!["login", "register"].includes(mode)) notFound();
  const { next } = await searchParams;
  return (
    <div className="wrap section-block narrow">
      <h1>{mode === "register" ? "Đăng ký" : "Đăng nhập"}</h1>
      <AuthForm register={mode === "register"} next={next} />
    </div>
  );
}
