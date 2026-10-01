# ADR-001: Lựa Chọn Mô Hình Kiến Trúc Phân Lớp (Clean Layered Architecture)

- **Ngày ban hành:** 2026-10-01
- **Trạng thái:** Accepted
- **Người đề xuất:** Architect (Sprint 0)
- **Các bên liên quan:** Coder, QA & Simulator, Security Auditor

---

## 1. Bối cảnh (Context & Problem Statement)
Hệ thống "Traffic Assistant" cần một kiến trúc phần mềm vừa đảm bảo tính module hóa cao để phát triển nhanh theo vòng lặp Sprint Agile, vừa dễ bảo trì, dễ viết unit test theo phương pháp TDD, và có thể khởi chạy gọn nhẹ bằng 1 câu lệnh (`run.bat` / `run.sh` / Docker). Cần quyết định giữa Kiến trúc Microservices phân tán hay Kiến trúc Phân lớp (Clean Layered Monolith).

---

## 2. Các Phương Án Cân Nhắc (Options Considered)

| Phương án | Ưu điểm | Nhược điểm | Đánh giá |
|---|---|---|---|
| **Phương án 1 (Được chọn): Clean Layered Architecture** | Phân tách rõ Domain, Application, Infrastructure, Presentation. Độ trễ thấp, không overhead mạng, test cực nhanh, chạy 1-click Docker. | Cần kỷ luật lập trình chặt chẽ để không vi phạm chiều phụ thuộc. | **Khuyến nghị** |
| **Phương án 2: Microservices** | Cô lập hoàn toàn từng service (Voice, Map, Hazard). | Quá phức tạp cho quy mô MVP, overhead distributed tracing, khó debug live và khởi chạy nặng nề. | Không chọn |
| **Phương án 3: Simple Flat Script (Monolithic Spaghetti)** | Viết nhanh trong 1 vài file script. | Không thể scale, không thể viết unit test độc lập, vi phạm nghiêm trọng chuẩn mực code. | Không chọn |

---

## 3. Quyết Định Được Chọn (Decision Outcome)
- **Quyết định:** Áp dụng **Clean Layered Architecture** với cấu trúc:
  - `core/`: Cấu hình, Logger JSON, Middleware.
  - `domain/`: Schemas, Value Objects, Entities độc lập.
  - `infrastructure/`: Kết nối kho lưu trữ, External APIs (OSRM), File store.
  - `application/`: Business Services (HazardService, RoutingService, VoiceIntentService).
  - `presentation/`: FastAPI Routers, PWA Web Client.
- **Cơ sở lý luận kỹ thuật (Rationale):** Đảm bảo tính độc lập của logic nghiệp vụ giao thông với chi tiết triển khai (DB hoặc API bên ngoài), cho phép viết unit test mô phỏng (mocking) cực kỳ dễ dàng.

---

## 4. Hậu Quả & Đánh Đổi (Consequences)
- **Tác động tích cực:** Codebase sạch, tuân thủ SOLID, dễ dàng phân chia task cho Coder, đạt coverage test > 80% nhanh chóng.
- **Tác động tiêu cực:** Cần tạo nhiều file DTO/Schema định nghĩa dữ liệu trung gian giữa các tầng.

---

## 5. Chỉ Dẫn Thực Thi Dành Cho Coder (Implementation Directive)
- Bước 1: Khởi tạo thư mục `backend/src/{core,domain,infrastructure,application,presentation}`.
- Bước 2: Tầng `domain` tuyệt đối không import ngược từ `infrastructure` hay `presentation`.
- Bước 3: Viết unit test cho tầng `application` sử dụng in-memory mock repository.

---

## 6. Tiêu Chí Nghiệm Thu Cho QA (Verification Criteria)
- Kiểm tra tính độc lập: chạy `pytest tests/` không yêu cầu kết nối mạng bên ngoài hay OSRM thật nhờ mock layer.
