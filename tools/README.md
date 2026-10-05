# Loop Engineering CLI Tools

Bộ công cụ dòng lệnh tiêu chuẩn tích hợp trong dự án **AutoCompliant-ML**:

---

## 1. `loop-gate` (Rào chắn an toàn tĩnh)
Kiểm tra danh sách tệp sắp commit/merge đối chiếu với chính sách trong [gate.yaml](file:///d:/CODE/AutoCompliant-ML/gate.yaml).

### Cách sử dụng:
```bash
# Qua npm script (nhanh nhất):
npm run gate

# Hoặc qua lệnh trực tiếp:
tools\loop-gate check --action commit --paths "loop/LOOP.md,loop/STATE.md" --gate-file gate.yaml

# Kiểm tra auto-merge:
tools\loop-gate check --action auto-merge --paths "docs/guide.md"
```

- **Mã phản hồi (Exit Codes)**:
  - `0`: Được phép thực thi (`ALLOWED [ok]`).
  - `2`: Chạm vào tệp cấm (`ESCALATE [denylist]`), cần con người duyệt.
  - `1`: Lỗi cú pháp hoặc thiếu cờ lệnh.

---

## 2. `loop-audit` (Kiểm toán cấu trúc Loop)
Quét toàn bộ cấu trúc dự án và chấm điểm độ sẵn sàng của vòng lặp tự hành (**Loop Readiness Score**).

### Cách sử dụng:
```bash
# Qua npm script:
npm run audit

# Hoặc qua lệnh trực tiếp:
tools\loop-audit .
```

---

## 3. `loop-context` (Quản lý ngân sách & Circuit Breaker)
Giám sát chi phí, token và số lần thử thất bại liên tiếp để tự động ngắt vòng lặp nếu agent bị kẹt hoặc lặp vô tận.

### Cách sử dụng:
```bash
tools\loop-context --check --ledger loop/loop-run-log.md
```
