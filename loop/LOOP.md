# AutoCompliant-ML Autonomous Engineering Loop

## Objective
Xây dựng pipeline Machine Learning thích ứng cấu hình & tối ưu hóa đa mục tiêu NSGA-II cho cơ cấu định vị vi mô đàn hồi (Compliant Mechanisms).

## Loop Protocol
1. **Read State**:
   - Đọc `STATE.md` để xác định Loop hiện tại đang thực thi (Loop 1 -> Loop 5).
   - Kiểm tra các task còn tồn đọng trong phần `Current Phase Tasks`.

2. **Execute (Minimal Diff)**:
   - Chỉ code các module thuộc Phase hiện tại.
   - Luôn viết/cập nhật unit test tương ứng trong `tests/` trước khi coi là xong task.
   - Không can thiệp sang các module thuộc Phase tương lai để tránh bùng nổ token/diff.

3. **Verify (Safety Gate)**:
   - Chạy lệnh kiểm tra được quy định trong `gate.yaml`:
     ```powershell
     pytest tests/ -v
     ```
   - Nếu test thất bại: Dừng lại sửa lỗi tại chỗ, tối đa 3 lần thử. Không được bỏ qua test.

4. **Update State & Logging**:
   - Cập nhật checklist và nhật ký lần chạy vào `STATE.md`.
   - Ghi chi tiết metric hoặc log vào `loop-run-log.md`.
