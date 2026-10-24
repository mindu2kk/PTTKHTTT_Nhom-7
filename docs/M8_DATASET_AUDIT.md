# M8 — kiểm toán dữ liệu

Nguồn/revision/license: xem M8_DATASET_SOURCES. Report gốc: `evidence/m8/dataset-audit.json`, import logs và ảnh QC cùng thư mục.

| Hạng mục | Số thực tế |
|---|---:|
| Record real_demo lưu trong DB, gồm nháp QC | 321 |
| Public/verified ảnh thật | 318 |
| Ảnh gallery liên kết public | 624 |
| Ảnh mở/đúng hash | 624 |
| Vector đúng model/revision/hash | 624 |
| Thiếu brand | 16 |
| Thiếu màu | 57 |
| Thiếu chất liệu | 189 |
| Giá nguồn VND merchant-verified | 0 |
| Tồn kho merchant-verified | 0 |

Category levels public: `{'0': 4, '1': 4, '2': 19}`. Giữ cây cũ riêng; thêm nhánh thực tế khi cần, không nhận đây là 4/11/34 đầy đủ của slide.

| Danh mục | Sản phẩm |
|---|---:|
| Bàn | 10 |
| Giày nam | 83 |
| Giày nữ | 83 |
| Bộ sạc | 19 |
| Loa | 3 |
| Tai nghe | 5 |
| Ốp điện thoại | 30 |
| Bàn phím | 4 |
| Gối | 5 |
| Ghế | 17 |
| Thảm | 15 |
| Ghế sofa | 13 |
| Đèn bàn | 7 |
| Dụng cụ nhà bếp | 8 |
| Phụ kiện máy tính | 9 |
| Máy pha cà phê | 1 |
| Chuột máy tính | 1 |
| Cốc | 4 |
| Chảo | 1 |

Import mở rộng tạo 309, tái sử dụng 11; replay cuối không tạo trùng. Pilot12 có1 swatch chuyển nháp/pending sau nhìn ảnh, không xóa raw/ảnh/đơn cũ. Gate từ chối loại này đã được thêm trước nhập mở rộng. Sau đó final QC320 primary phát hiện thêm2 logo/placeholder, đã chuyển nháp/quarantine và thêm denylist để không nhập lại. Catalog cuối lấy số thực tế trong bảng trên, không làm tròn thành320. Fixtures M7 không vào profile real_demo.

Một primary trên mỗi sản phẩm, tối đa một ảnh phụ được chọn khi hợp lệ; thiếu ảnh phụ không phải thiếu ảnh chính. Thumbnail320 cho mỗi ảnh; tổng derivative main WebP public khoảng 38.22 MiB, chưa gồm thumbnail/raw/private. Nội dung ảnh nguồn có thể gồm bố cục catalog, nền trắng, chữ chú thích; không gọi đây là bộ ảnh smartphone tự chụp.

Tên Việt từ mapping loại/brand/model, tên gốc giữ ở detail và raw. Màu ánh xạ khi có bằng chứng, vật liệu nguồn có thể vẫn nguyên ngôn ngữ. Không bịa thuộc tính thiếu, review/sales/stock. Offer và hạn mức đặt thử nằm tách metadata thật, nhãn rõ. Mục tiêu pilot300–500 đạt sau loại2 placeholder; chưa mở rộng/đo catalog thật1000/3000.
