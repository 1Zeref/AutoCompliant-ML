# Antigravity Project Rules & Operating Principles

## 1. Loop Engineering Protocol
- Mọi chu kỳ thực thi (iteration) đều phải tuân theo vòng lặp được định nghĩa trong `loop/LOOP.md`.
- Trước khi thực hiện bất kỳ thay đổi nào, agent bắt buộc phải đọc `loop/STATE.md` để nắm bắt trạng thái hiện tại, mục tiêu của chu kỳ và các rào cản (blockers).
- Sau khi hoàn thành một nhiệm vụ, agent phải cập nhật kết quả và chuyển trạng thái trong `loop/STATE.md`.

## 2. Minimal Blast Radius (Phạm vi tác động tối thiểu)
- Áp dụng triệt để nguyên lý `skills/minimal-fix.md`.
- Chỉ sửa đổi chính xác những tệp và dòng code liên quan trực tiếp đến mục tiêu của chu kỳ hiện tại.
- Không tự ý tái cấu trúc (refactor) các module không liên quan, không xóa comment hoặc đổi format toàn diện của codebase.

## 3. Automated Gate Verification (Rào chắn kiểm thử)
- Mọi thay đổi phải vượt qua các tiêu chí nghiệm thu được khai báo trong `loop/gate.yaml`.
- Nếu có bài kiểm thử hoặc gate kiểm tra thất bại, ưu tiên sửa lỗi ngay trong chu kỳ hiện tại trước khi chuyển sang tác vụ mới.

## 4. State Persistence (Lưu trữ trạng thái liên tục)
- Không dựa hoàn toàn vào bộ nhớ ngữ cảnh hội thoại (context window).
- Mọi quyết định quan trọng, mã lỗi phát hiện được, và tiến độ công việc phải được ghi lại rõ ràng trong `loop/STATE.md`.
