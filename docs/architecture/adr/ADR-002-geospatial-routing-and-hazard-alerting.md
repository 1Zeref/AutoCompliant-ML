# ADR-002: Động Cơ Định Tuyến Xe Máy & Cảnh Báo An Toàn Địa Không Gian (Geospatial Hazard Alerting)

- **Ngày ban hành:** 2026-10-01
- **Trạng thái:** Accepted
- **Người đề xuất:** Architect (Sprint 0)
- **Các bên liên quan:** Coder, QA & Simulator, Security Auditor

---

## 1. Bối cảnh (Context & Problem Statement)
Người đi xe máy tại đô thị Việt Nam cần tìm đường nhanh, tuy nhiên cần được cảnh báo sớm trước 100m - 300m khi sắp tiếp cận camera phạt nguội, điểm đen ngập úng mùa mưa, hoặc đoạn đường giới hạn tốc độ. Cần một cơ chế tính toán định tuyến và kiểm tra vùng an toàn (Geofencing) vừa chính xác, vừa có độ trễ cực thấp (< 50ms per check), hoạt động độc lập không phụ thuộc vào API tính phí như Google Maps.

---

## 2. Các Phương Án Cân Nhắc (Options Considered)

| Phương án | Ưu điểm | Nhược điểm | Đánh giá |
|---|---|---|---|
| **Phương án 1 (Được chọn): OSRM Routing + Haversine Geofencing Engine với Fallback Graph** | Miễn phí, mã nguồn mở, hỗ trợ profile xe máy/ô tô; thuật toán khoảng cách Haversine tính toán cục bộ đạt tốc độ hàng chục nghìn điểm/giây; có thuật toán nội bộ Fallback khi mất mạng. | Cần tự quản lý và cập nhật tập dữ liệu điểm đen giao thông (GeoJSON/Database). | **Khuyến nghị** |
| **Phương án 2: Google Directions & Distance Matrix API** | Dữ liệu chính xác toàn cầu, cập nhật kẹt xe theo thời gian thực. | Chi phí tốn kém, không cho phép can thiệp thuật toán tránh điểm ngập úng tùy biến của người dùng; dễ cạn quota. | Không chọn |
| **Phương án 3: PostgreSQL + PostGIS container độc lập** | Hỗ trợ hàm không gian ST_DWithin cực mạnh. | Tăng dung lượng Docker image lên thêm 500MB và thời gian build lâu, tiêu tốn RAM khi chạy cục bộ. | Dành cho quy mô mở rộng sau này |

---

## 3. Quyết Định Được Chọn (Decision Outcome)
- **Quyết định:**
  - Sử dụng **OSRM (Open Source Routing Machine) API** công cộng / self-hosted để lấy polyline lộ trình xe máy.
  - Xây dựng **Spatial Hazard Engine** trên Python sử dụng công thức **Haversine Distance**:
    $$d = 2r \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)} \right)$$
  - Tạo thuật toán **Hazard-Aware Route Penalty**: Nếu cung đường đi qua vùng ngập úng hoặc kẹt xe, hệ thống sẽ đề xuất lộ trình thay thế (Alternative Route).
  - Tích hợp sẵn cơ chế **Fallback Routing Engine** dựa trên lưới tọa độ A* nội bộ khi kết nối mạng OSRM gặp sự cố.

---

## 4. Hậu Quả & Đánh Đổi (Consequences)
- **Tác động tích cực:** Hoạt động nhanh, chi phí 0đ, phản hồi vị trí định vị tức thì (< 20ms).
- **Tác động tiêu cực:** Cần xây dựng sẵn bộ dữ liệu mẫu (Seed Data) chất lượng cao về các điểm camera phạt nguội và điểm ngập úng tại các tuyến đường huyết mạch (TP.HCM / Hà Nội).

---

## 5. Chỉ Dẫn Thực Thi Dành Cho Coder (Implementation Directive)
- Bước 1: Viết module `backend/src/infrastructure/seed_data.py` chứa danh sách điểm nóng giao thông chuẩn GeoJSON.
- Bước 2: Hiện thực hóa class `HazardService` với hàm `check_proximity(user_lat, user_lon, heading, speed)`.
- Bước 3: Hiện thực hóa class `RoutingService` với phương thức `get_directions(start, end, avoid_hazards=True)`.

---

## 6. Tiêu Chí Nghiệm Thu Cho QA (Verification Criteria)
- Giả lập vị trí người dùng di chuyển dần về phía Camera Phạt Nguội tại Ngã tư Hàng Xanh. Khi khoảng cách $\le 200\text{m}$, API trả về cờ cảnh báo `danger` kèm tin nhắn âm thanh cần phát.
