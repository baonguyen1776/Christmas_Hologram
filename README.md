# 🎄 Hologram Cây Thông Noel Tương Tác (Hand Tracking)

Đây là ứng dụng Python tạo hiệu ứng cây thông Noel 3D lung linh, có thể điều khiển bằng cử chỉ tay qua webcam. Bạn có thể làm cây thông nổ tung thành vũ trụ, xoay/chọn ảnh kỷ niệm, và trang trí chữ chúc mừng lấp lánh!

## ✨ Tính năng nổi bật

- **Cây thông 3D**: Hiệu ứng lung linh, chuyển động đẹp mắt
- **Nhận diện bàn tay**: Điều khiển bằng webcam
- **Tương tác**: 
  - Giơ 2 ngón tay: Cây thông nổ thành các hạt vũ trụ
  - Thu tay lại: Cây thông trở lại bình thường
  - Vuốt: Xoay chuyển các ảnh kỷ niệm
  - Chạm/Zoom: Phóng to ảnh
- **Chữ chúc mừng lấp lánh**: Trang trí đẹp như thiệp
- **Ảnh kỷ niệm**: Ảnh bay quanh cây thông

## 📋 Yêu cầu

- Python 3.8 trở lên
- Webcam
- Thư viện: OpenCV, Pygame, MediaPipe

## 🚀 Cài đặt & Sử dụng

### 1. Tải mã nguồn
```bash
git clone <link-repo-của-bạn>
cd Christmas_Hologram
```

### 2. Tạo môi trường ảo
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Cài thư viện phụ thuộc
```bash
pip install -r requirements.txt
```

### 4. Thêm ảnh của bạn vào thư mục `assets/`

- Định dạng: `.jpeg`, `.jpg`, `.png`
- Kích thước khuyên dùng: 400x300px trở lên
- Không giới hạn ảnh: "Khuyến khích càng nhiều càng tốt"

Ví dụ:
```
assets/
├── GreatVibes-Regular.ttf   (font đã có sẵn)
├── anh1.jpeg                (bạn tự thêm)
├── anh2.jpeg
├── anh3.jpeg
└── anh4.jpeg
```

### 5. Tuỳ chỉnh chữ chúc mừng (không bắt buộc)

Mở file `config.py` và sửa dòng:
```python
TITLE_TEXT = 'Chúc Công Chúa Noel zui zẻ'  # Đổi thành lời chúc của bạn
TITLE_MAIN_COLOR = (255, 255, 255)         # Đổi màu chữ nếu muốn
TITLE_FONT_SIZE = 80                       # Đổi cỡ chữ nếu muốn
```

## ▶️ Chạy chương trình

### Bắt đầu ứng dụng
```bash
python main_interactive.py
```

### Điều khiển

| Phím/Cử chỉ          | Tác dụng                   |
| -------------------- | -------------------------- |
| **SPACE**            | Đổi giữa chế độ cây/vũ trụ |
| **SPACE (trên ảnh)** | Phóng to ảnh               |
| **2 ngón tay**       | Làm cây thông nổ thành hạt |
| **Vuốt**             | Xoay chuyển các ảnh        |
| **Chụm/Zoom**        | Phóng to ảnh               |
| **D**                | Hiện thông tin debug       |
| **ESC**              | Thoát chương trình         |

## 📁 Cấu trúc thư mục

```
Christmas_Hologram/
├── main_interactive.py      # Chạy chính
├── config.py                # Tuỳ chỉnh chữ, màu, font
├── requirements.txt         # Thư viện cần thiết
├── README.md                # File hướng dẫn này
├── assets/                  # Ảnh & font
│   ├── GreatVibes-Regular.ttf
│   └── anh-cua-ban.jpeg     # Thêm ảnh vào đây
├── core/
│   ├── core_hand_tracking.py
│   ├── gesture_controller.py
│   └── state_manager.py
└── scenes/
    └── tree_3d.py           # Vẽ cây thông 3D
```

## 🎨 Tuỳ chỉnh nhanh

- Đổi lời chúc: Sửa `TITLE_TEXT` trong `config.py`
- Đổi màu chữ: Sửa `TITLE_MAIN_COLOR` (giá trị RGB)
- Thêm ảnh: Chỉ cần copy ảnh vào `assets/` rồi chạy lại
- Đổi cỡ chữ: Sửa `TITLE_FONT_SIZE` trong `config.py`

## 🐛 Lỗi thường gặp

- **Không nhận webcam?** 
  - Kiểm tra quyền truy cập camera trong cài đặt hệ thống
  - Đảm bảo ánh sáng đủ
  - Có thể đổi `camera_id=1` trong code nếu cần

- **Ảnh không hiện?** 
  - Ảnh phải nằm trong thư mục `assets/`
  - Đúng định dạng: `.jpeg`, `.jpg`, hoặc `.png`
  - Tên file không có dấu cách

- **Chạy chậm?** 
  - Giảm `TITLE_FONT_SIZE` trong `config.py`
  - Đóng bớt ứng dụng khác
  - Kiểm tra lại cài đặt độ phân giải camera

## 📝 Giấy phép

Miễn phí sử dụng, tuỳ ý chỉnh sửa. Chúc bạn một mùa Noel vui vẻ! 🎅✨