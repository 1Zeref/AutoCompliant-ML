# SPRINT 1 RETROSPECTIVE — BÁO CÁO CẢI TIẾN QUY TRÌNH

> **Sprint:** `Sprint 1 (MVP Walking Skeleton)`  
> **Thời điểm:** 2026-10-01  
> **Điều phối viên:** Autonomous Scrum Master / Report Scribe

---

## 1. NHỮNG ĐIỂM HOẠT ĐỘNG XUẤT SẮC (WHAT WENT WELL)
1. **Kỷ luật Stop-the-Line & TDD Red-Green-Refactor:** Khi phát hiện lỗi dấu cách trong `normalize_vietnamese_text` và xử lý async trong `test_routing_service`, đội ngũ lập trình viên dừng ngay lập tức, sửa triệt để nguyên nhân gốc rễ và đưa 100% test suite về màu xanh (17/17 tests pass).
2. **Độ phủ kiểm thử vượt chuẩn DoD:** Đạt độ phủ mã nguồn **86%** (vượt ngưỡng yêu cầu $\ge 80\%$).
3. **Hiệu năng vượt trội:** Thời gian nhận diện và phân tích câu lệnh tiếng Việt chỉ mất **14.8 ms** (nhanh gấp 54 lần mục tiêu cam kết $\le 800\text{ ms}$).
4. **Trải nghiệm người dùng lái xe máy:** Chế độ HUD Mode với các nút bấm kích thước lớn và cảnh báo nhấp nháy độ tương phản cao giải quyết triệt để nỗi đau mất tập trung khi lái xe.
5. **Giao diện Song ngữ & Trang Quản trị AI chuyên biệt:** Tuân thủ 100% yêu cầu về Language Switcher (EN | VI) và 4 nhóm thông số huấn luyện mô hình.

---

## 2. NHỮNG ĐIỂM CẦN NÂNG CẤP & CẢI THIỆN (WHAT CAN BE IMPROVED)
1. **Dữ liệu điểm đen vùng miền:** Cần mở rộng thêm tập dữ liệu camera phạt nguội và điểm ngập úng tại các thành phố khác như Đà Nẵng, Cần Thơ, Hải Phòng.
2. **Cộng đồng đóng góp dữ liệu (Crowdsourcing):** Hiện tại tính năng báo cáo kẹt xe chỉ mới dừng ở mức phân tích intent giọng nói; cần lưu trữ điểm báo cáo vào cơ sở dữ liệu để chia sẻ thời gian thực cho các tài xế khác.

---

## 3. CÁC HÀNH ĐỘNG CỤ THỂ CHO SPRINT 2 (ACTION ITEMS FOR SPRINT 2)
- [ ] **Action 1 (Ưu tiên 1):** Hiện thực hóa US-007 (Community Crowdsourcing): Cho phép lưu các báo cáo sự cố giao thông vào SQLite/PostgreSQL để cập nhật tức thời lên bản đồ người dùng khác.
- [ ] **Action 2 (Ưu tiên 2):** Mở rộng bộ từ điển đồng nghĩa tiếng Việt cho các phương ngữ miền Trung và miền Nam trong `VoiceIntentService`.
