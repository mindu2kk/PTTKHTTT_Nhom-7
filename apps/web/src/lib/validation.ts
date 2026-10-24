import { z } from "zod";
export const credentialsSchema = z.object({
  email: z.email("Email không hợp lệ.").max(250),
  password: z.string().min(10, "Mật khẩu cần ít nhất 10 ký tự.").max(128),
});
export const addressSchema = z.object({
  recipient: z.string().trim().min(2, "Hãy nhập tên người nhận.").max(100),
  phone: z.string().regex(/^\+?[0-9 ]{9,15}$/, "Số điện thoại không hợp lệ."),
  address_line: z.string().trim().min(8, "Hãy nhập địa chỉ đầy đủ.").max(300),
});
