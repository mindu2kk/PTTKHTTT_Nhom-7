# M8 — nguồn dữ liệu và quyền ảnh

Kiểm tra trực tiếp ngày 2026-10-22. Không scrape Shopee/Tiki, không vượt chặn, không dùng URL ảnh công khai làm bằng chứng cấp phép.

| Nguồn | Availability/revision thực đã kiểm | Quyền và quyết định |
|---|---|---|
| [ABO chính thức](https://registry.opendata.aws/amazon-berkeley-objects/) | S3 công khai, không cần tài khoản. `listings_0.json.gz` 5.446 MB, ETag/MD5 `49304dd0edc3aa3d4cb19231927732fc`; 9.232 raw records. `images.csv.gz` khoảng 6.43 MB, SHA256 trong audit | **Được duyệt**. [README toàn bộ](https://amazon-berkeley-objects.s3.amazonaws.com/README.md), [README ảnh](https://amazon-berkeley-objects.s3.amazonaws.com/images/README.md), [CC BY 4.0](https://amazon-berkeley-objects.s3.amazonaws.com/LICENSE-CC-BY-4.0.txt) áp dụng cả dữ liệu và ảnh. AWS ghi license đã đổi từ NC sang BY năm 2023; không dùng blog cũ để kết luận NC. |
| [allietran/CAMEO](https://huggingface.co/datasets/allietran/CAMEO) | API metadata HTTP200, revision `901b4fd7f175cdd5522964034d449e6f9b570c7c`; products 4.09k trong viewer, có `product_id/shop_id/image_path/price/product_name` | Card CC BY-NC-SA 4.0; chưa đủ bằng chứng quyền tái xuất bản ảnh merchant. Chỉ metadata/card đã kiểm; không tải/nhập ảnh, không publish. Giá nguồn không được xem là chào bán hiện tại. |
| [ceyda/fashion-products-small](https://huggingface.co/datasets/ceyda/fashion-products-small) | HTTP200, revision `ef520080129df6ec7fda0df347b5f7eacdf0dc1c`; [README](https://huggingface.co/datasets/ceyda/fashion-products-small/raw/main/README.md) dẫn bản tiền xử lý từ Kaggle, ảnh thu nhỏ512 | Không có license trong card metadata đã nhận; quyền từng ảnh chưa rõ. Không tải/nhập/publish. Không suy ra quyền từ repository public. |
| [arturayupov/womens-fashion-catalog](https://huggingface.co/datasets/arturayupov/womens-fashion-catalog) | HTTP200, revision `476c18f8cd1f7d9c2553ed30b08de02e1eba2e1f`; card ghi2.766 products,12.978 image URLs,16.989 variants,158 collections; tổng32.891 là tổng hàng nhiều bảng, không phải số sản phẩm | Publisher Arcada LLC/Livostyle ghi MIT, dữ liệu catalog từ Shopify. Là ứng viên có triển vọng; M8 chọn ABO có archive ảnh cùng giấy phép rõ để tránh thêm phụ thuộc ảnh CDN/quyền theo từng tài sản. Nguồn này chưa được duyệt vào catalog trong đợt này; không kết luận rằng ảnh của họ bị cấm sử dụng. |

## Ghi nguồn bắt buộc

Dữ liệu và ảnh © Amazon.com. Công trình xây dựng dataset: Matthieu Guillaumin, Thomas Dideriksen, Kenan Deng, Himanshu Arora, Jasmine Collins, Jitendra Malik. CC BY 4.0; không có bảo đảm hoặc bảo trợ, không suy ra quyền thương hiệu. Hiển thị tại `/sources`, footer và liên kết từ trang sản phẩm. Thay đổi: chọn subset, ánh xạ tên/nhóm tiếng Việt, giữ tên gốc, bỏ EXIF và tạo WebP960/320.

`data/sources/abo-rights.json` là quyết định quyền có revision; pipeline phải kiểm trước tải/nhập. Raw, originals và qrels staging ở `data/private/m8`; chỉ derivative được duyệt ở `data/catalog/images`. Không có ảnh từ các nguồn chưa duyệt đi vào catalog.

## Phạm vi thương mại

ABO không cung cấp giá VND và tồn kho merchant được xác minh cho cửa hàng này. `real_demo` chứa metadata/ảnh thật, **offer mô phỏng riêng** và **hạn mức đặt thử5**, không gọi là tồn kho Amazon. Không quy đổi giá nguồn, không tạo review/rating/lượt bán/khuyến mại. Chỉ checkout mô phỏng/COD demo. Nhóm thời trang hiện chủ yếu là giày dép, không tuyên bố đã có catalog quần áo đầy đủ.
