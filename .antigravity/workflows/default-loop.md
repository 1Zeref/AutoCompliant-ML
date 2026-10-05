# Default Loop Workflow

## Trigger
Thực thi theo từng chu kỳ công việc hoặc khi người dùng yêu cầu tiếp tục vòng lặp (Next Loop Iteration).

## Các bước thực hiện:
1. **Đọc State**: Xem `loop/STATE.md` để lấy mục tiêu tiếp theo (`Next Action`).
2. **Triển khai**: Thực hiện code/fix theo nguyên tắc tối thiểu (`skills/minimal-fix.md`).
3. **Chạy Gate**: Chạy bộ kiểm thử tự động theo `loop/gate.yaml`.
4. **Cập nhật State**: Ghi nhận kết quả, nhật ký chu kỳ vào `loop/STATE.md`.
