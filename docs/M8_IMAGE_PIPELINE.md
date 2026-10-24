# M8 — ảnh thật và ánh xạ

1. Kiểm `abo-rights.json` approved/CC-BY-4.0/revision. Chỉ S3 dataset chính thức; không dùng CDN merchant ngoài dataset.
2. Cache metadata gzip; verify MD5 shard đã pin, ghi SHA256 listing/image metadata. ID ngoài là `(domain_name,item_id)`, ID nội bộ là SHA256 rút gọn có namespace `abo-`.
3. Chỉ loại có mapping rõ và tên tiếng Anh để ánh xạ nhãn tiếng Việt; giữ nguyên tên nguồn. Các record không đủ ID/ảnh/ngôn ngữ/mapping không được chọn. Loại `swatch/sample/replacement` để không gán ảnh mẫu vải thành sofa.
4. Resolve `main_image_id/other_image_id` qua images.csv đúng product. Tải chọn lọc, tối đa2 gallery ảnh/sản phẩm. Cache/partial Range hỗ trợ tiếp tục, giới hạn5MB/tệp, tối đa4 tải đồng thời. Không tải archive ảnh nhiều GB.
5. Pillow decode thật; JPEG/PNG/WebP, giới hạn12MP và tối thiểu80px. EXIF transpose, RGB, bỏ metadata, WebP960 và thumbnail320. Không đổi ảnh sản phẩm bằng ảnh ngẫu nhiên hoặc ảnh sinh.
6. Dedup external ID, main image ID và SHA256 ảnh chính. Không hợp nhất hai SKU theo tên. Nhãn group/category phải khớp mapping loại nguồn; dry-run kiểm hash/decode/đường dẫn/mapping/quyền trước transaction.
7. Một primary duy nhất bằng partial UNIQUE index; nhiều ảnh thêm trong `product_images` qua migration0005. Listing chọn primary; detail chỉ trả gallery có quyền. Ảnh/index gắn đúng product ID xuyên filter/cart/order.
8. Chỉ derivative đã duyệt ở `data/catalog/images`, bind mount read-only vào API. Static ETag và revalidation; JSON nghiệp vụ vẫn no-store. Không lưu ảnh người dùng vào thư mục này.

## QC thực tế

Pilot12/23 ảnh đã nhập/index. Nhìn screenshot phát hiện một source title là “Swatch” nhưng type SOFA; chuyển sản phẩm pilot đó thành draft/pending, giữ raw và ảnh để audit. Dry-run đợt mở rộng từ chối toàn transaction; sau đó sửa mapping, thu thập lại từ cache và nhập lại. Xem `visual-qc-correction.json` và `dry-run-rejected-swatch.txt`. Không gọi lần đầu thất bại là pass.

Kiểm kỹ thuật không thay thế nhìn toàn bộ ảnh cho mọi ngữ cảnh sử dụng. Số record/ảnh/thumbnail/index thực tế và ảnh query giữ riêng nằm trong DATASET_AUDIT/TEST_REPORT. Không có ảnh người dùng bị tái sử dụng làm tài sản catalog.

Final review320 primary contact sheets phát hiện thêm logo và Image Coming Soon. Hai record được chuyển draft/pending, derivative đưa vào private quarantine; denylist abo-image-qc.json ngăn nhập lại. Catalog cuối318 sản phẩm/624 ảnh, tương ứng1248 tệp derivative có tham chiếu. Review subset318 IDs được lưu riêng; nhập ngoài danh sách bị chặn trước publication.
