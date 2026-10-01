# SPRINT 1 BACKLOG — MVP WALKING SKELETON

> **Sprint:** `Sprint 1`  
> **Thời lượng:** 2 tuần (hoặc tương đương chu trình hoàn tất MVP)  
> **Sprint Goal (Mục tiêu Sprint):** *Hiện thực hóa trọn vẹn bản phát hành shippable (Walking Skeleton) của Vietnam Motorbike Smart Traffic Assistant: Backend FastAPI Clean Layered, Spatial Hazard Alerting, OSRM Routing tránh ngập, Voice Assistant tiếng Việt rảnh tay, Giao diện PWA Song ngữ (EN/VI) kèm chế độ HUD xe máy, Trang Quản trị Huấn luyện Mô hình chuyên biệt, và đóng gói Docker 1-click chạy qua run.bat/run.sh.*  
> **Tổng Story Points cam kết:** 26 Points

---

## 1. DANH SÁCH USER STORIES ĐÃ CAM KẾT & PHÂN RÃ KỸ THUẬT

### US-001: Core Architecture, Docker Multi-Stage & Day-1 Healthcheck (3 Points)
- **Tasks Kỹ thuật:**
  - [ ] `T-101`: Thiết lập cấu trúc thư mục `backend/src/{core,domain,infrastructure,application,presentation}`.
  - [ ] `T-102`: Tạo `backend/src/core/config.py` và `backend/src/core/logger.py` hỗ trợ Structured JSON Log và Correlation ID.
  - [ ] `T-103`: Viết router `GET /api/v1/health` trả về status, version và uptime.
  - [ ] `T-104`: Viết `Dockerfile` và `docker-compose.yml` multi-stage tối ưu, tạo `run.bat` và `run.sh`.
  - [ ] `T-105`: Viết unit test cho config và health check (`tests/test_api_endpoints.py`).

---

### US-002: Spatial Hazard Alerting (Camera phạt nguội, Điểm ngập, Tốc độ) (5 Points)
- **Tasks Kỹ thuật:**
  - [ ] `T-201`: Định nghĩa Domain Schema `Hazard`, `HazardType`, `ProximityAlert` tại `backend/src/domain/hazard.py`.
  - [ ] `T-202`: Xây dựng `backend/src/infrastructure/seed_data.py` chứa 20+ điểm đen giao thông thực tế tại TP.HCM (Hàng Xanh, Nguyễn Hữu Cảnh, Võ Văn Kiệt, Phạm Văn Đồng) và Hà Nội.
  - [ ] `T-203`: Hiện thực hóa `backend/src/application/hazard_service.py` với thuật toán khoảng cách Haversine và logic geofencing.
  - [ ] `T-204`: Viết API Endpoints `GET /api/v1/hazards` và `POST /api/v1/hazards/check-proximity`.
  - [ ] `T-205`: Viết unit tests TDD cho `HazardService` kiểm tra geofencing và câu phát âm cảnh báo âm thanh (`tests/test_hazard_service.py`).

---

### US-003: Motorbike Route Engine & Hazard Avoidance (5 Points)
- **Tasks Kỹ thuật:**
  - [ ] `T-301`: Định nghĩa Domain Schema `RouteRequest`, `RouteResult`, `Waypoint` tại `backend/src/domain/route.py`.
  - [ ] `T-302`: Xây dựng `backend/src/infrastructure/osrm_client.py` gọi OSRM Driving/Bike API kèm Fallback Engine khi offline.
  - [ ] `T-303`: Hiện thực hóa `backend/src/application/routing_service.py`: tính toán lộ trình, phát hiện điểm nguy hiểm trên tuyến đường và hỗ trợ cờ `avoid_floods`.
  - [ ] `T-304`: Viết API Endpoint `POST /api/v1/routes/directions`.
  - [ ] `T-305`: Viết unit test TDD cho `RoutingService` (`tests/test_routing_service.py`).

---

### US-004: Hands-Free Vietnamese Voice Assistant & NLP Intent Engine (5 Points)
- **Tasks Kỹ thuật:**
  - [ ] `T-401`: Định nghĩa Domain Schema `VoiceRequest`, `VoiceResponse`, `IntentType` tại `backend/src/domain/voice.py`.
  - [ ] `T-402`: Xây dựng `backend/src/application/voice_intent_service.py` phân tích ý định tiếng Việt (`NAVIGATE`, `CHECK_HAZARDS`, `CHECK_FLOOD_WEATHER`, `REPORT_INCIDENT`, `HELP_GUIDE`) và trích xuất điểm đến.
  - [ ] `T-403`: Viết API Endpoint `POST /api/v1/voice/parse`.
  - [ ] `T-404`: Tích hợp bộ nhận diện giọng nói Web Speech API (`SpeechRecognition`) và tổng hợp giọng nói (`speechSynthesis`) tại frontend.
  - [ ] `T-405`: Viết unit test TDD cho phân loại Intent tiếng Việt (`tests/test_voice_nlp.py`).

---

### US-005: Mobile-First Bilingual PWA Client (EN/VI) & Motorbike HUD Mode (5 Points)
- **Tasks Kỹ thuật:**
  - [ ] `T-501`: Tạo bộ từ điển ngôn ngữ `frontend/locales/en.json` và `frontend/locales/vi.json`.
  - [ ] `T-502`: Xây dựng giao diện `frontend/index.html` với Tailwind CSS responsive, nút Language Switcher (EN | VI) trên Header.
  - [ ] `T-503`: Tích hợp bản đồ tương tác Leaflet.js hiển thị markers, polyline lộ trình và vòng bán kính cảnh báo nguy hiểm.
  - [ ] `T-504`: Xây dựng chế độ Motorbike HUD Mode với nút bấm Micro siêu to, hiển thị cảnh báo nhấp nháy độ tương phản cao ban đêm.
  - [ ] `T-505`: Tạo tệp `manifest.json` và Service Worker cơ bản hỗ trợ PWA cài đặt trên màn hình điện thoại.

---

### US-006: Dedicated Model Training / Fine-Tuning Management Page (3 Points)
- **Tasks Kỹ thuật:**
  - [ ] `T-601`: Tạo `backend/src/application/training_service.py` quản lý dataset mẫu câu, trạng thái huấn luyện và metrics.
  - [ ] `T-602`: Viết API Endpoints `GET /api/v1/training/status` và `POST /api/v1/training/train` (async execution).
  - [ ] `T-603`: Xây dựng giao diện `frontend/static/training.html` và `training.js` với 4 nhóm thông số chuẩn (Dataset, Basic Hyperparams, Architecture & LoRA, Checkpoint/Evaluation).
  - [ ] `T-604`: Thêm liên kết điều hướng từ Navbar chính sang trang Training và hỗ trợ song ngữ EN/VI.
  - [ ] `T-605`: Viết unit test cho Training Service (`tests/test_api_endpoints.py`).

---

## 2. BẢNG TIÊU CHÍ HOÀN THÀNH (DEFINITION OF DONE - DoD)

Một User Story chỉ được đóng `[x] DONE` khi:
- [ ] 100% Acceptance Criteria đã được kiểm thử và Pass.
- [ ] Unit tests đã viết và pass với test coverage $\ge 80\%$.
- [ ] Trụ cột 3 (QA) xác nhận 0 Critical Bug, 0 Major Bug.
- [ ] Trụ cột 4 (Security) xác nhận không có lỗ hổng bảo mật nghiêm trọng (OWASP / Dependency audit).
- [ ] Hệ thống khởi động thành công với lệnh `run.bat` / `docker compose up`.
