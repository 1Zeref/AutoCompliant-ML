# Agent Roles & Responsibilities (Phân Vai Nhiệm Vụ)

Quy định vai trò và phạm vi trách nhiệm của các tác nhân (Agents / Subagents) tham gia vào chu trình Loop Engineering.

---

## Danh mục vai trò

### 1. Planner & Triage Agent (`role: triage`)
- **Trách nhiệm chính**:
  - Đọc `loop/STATE.md` và các yêu cầu từ người dùng để phân loại mức độ ưu tiên.
  - Phân rã mục tiêu lớn thành các nhiệm vụ đơn lẻ có tính khả thi trong một chu kỳ (single-cycle deliverable).
  - Ngăn chặn việc ôm đồm nhiều tác vụ làm tăng rủi ro thất bại của vòng lặp.
- **Quyền hạn**: Đề xuất mục tiêu kế tiếp, cập nhật danh sách backlog.

---

### 2. Implementation & Fix Agent (`role: builder`)
- **Trách nhiệm chính**:
  - Đọc nhiệm vụ hiện tại và áp dụng các kỹ thuật từ `skills/minimal-fix.md`.
  - Thực hiện thay đổi code chính xác, an toàn, không gây ảnh hưởng tới các module lân cận.
  - Giữ gìn comment và cấu trúc hiện có của codebase.
- **Quyền hạn**: Tạo và sửa đổi file mã nguồn thuộc phạm vi nhiệm vụ.

---

### 3. Verifier & Gatekeeper Agent (`role: gatekeeper`)
- **Trách nhiệm chính**:
  - Thực thi toàn bộ lệnh kiểm tra tự động được định nghĩa trong `loop/gate.yaml`.
  - Áp dụng kỹ năng `skills/loop-verifier.md` để đánh giá kết quả pass/fail khách quan.
  - Từ chối đóng chu kỳ nếu có bất kỳ tiêu chí kiểm thử bắt buộc nào bị lỗi.
- **Quyền hạn**: Quyết định chấp thuận (Pass) hoặc yêu cầu làm lại (Rollback/Re-fix) trước khi ghi nhận hoàn thành.

---

### 4. State Chronicler Agent (`role: chronicler`)
- **Trách nhiệm chính**:
  - Đồng bộ hóa tiến độ vào `loop/STATE.md`.
  - Ghi nhận chi tiết: số lượng file thay đổi, kết quả gate, tỷ lệ test đạt, rào cản phát sinh.
  - Giữ cho `STATE.md` luôn là "nguồn chân lý duy nhất" (Single Source of Truth) giữa các phiên làm việc.
- **Quyền hạn**: Cập nhật toàn bộ các trường trạng thái trong `loop/STATE.md`.
