# Antigravity Task Loop

## Objective
[Mô tả mục tiêu ngắn gọn cần đạt được trong session này]

## Execution Protocol
1. **Read State**: Đọc `loop/STATE.md` để nắm các công việc đã làm và task hiện tại.
2. **Execute**:
   - Chỉ sửa đổi mã nguồn tương ứng với 1 task nhỏ (Minimal Diff).
   - Không refactor lan man ngoài phạm vi task.
3. **Verify**:
   - Chạy lệnh test/lint tương ứng.
   - Nếu test fail: quay lại bước 2 để sửa, tối đa 3 lần thử.
4. **Update State**:
   - Cập nhật kết quả vào `loop/STATE.md`.
   - Ghi log vào `loop/loop-run-log.md`.
