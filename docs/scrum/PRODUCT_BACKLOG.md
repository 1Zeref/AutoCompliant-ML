# PRODUCT BACKLOG — VIETNAM MOTORBIKE SMART TRAFFIC ASSISTANT

> **Dự án:** Vietnam Motorbike Smart Traffic Assistant  
> **Product Owner:** Autonomous Orchestrator  
> **Quy ước:** Chuẩn hóa INVEST, MoSCoW và Fibonacci Story Points (1, 2, 3, 5, 8, 13)

---

## 1. TỔNG QUAN PRODUCT BACKLOG

| Mã Story | Tên User Story | Story Points | Ưu tiên | Trạng thái | Sprint dự kiến |
|:---|:---|:---:|:---:|:---:|:---:|
| **US-001** | Core Architecture, Docker Multi-Stage & Day-1 Healthcheck | 3 | Must Have | Ready | Sprint 1 |
| **US-002** | Spatial Hazard Alerting (Camera phạt nguội, Điểm ngập, Tốc độ) | 5 | Must Have | Ready | Sprint 1 |
| **US-003** | Motorbike Route Engine & Hazard Avoidance | 5 | Must Have | Ready | Sprint 1 |
| **US-004** | Hands-Free Vietnamese Voice Assistant & NLP Intent Engine | 5 | Must Have | Ready | Sprint 1 |
| **US-005** | Mobile-First Bilingual PWA Client (EN/VI) & Motorbike HUD Mode | 5 | Must Have | Ready | Sprint 1 |
| **US-006** | Dedicated Model Training / Fine-Tuning Management Page | 3 | Must Have | Ready | Sprint 1 |
| **US-007** | Community Traffic Incident Crowdsourcing & Live Feedback | 5 | Should Have | Backlog | Sprint 2 |
| **US-008** | Real-time Weather & Flash Flood Forecast Integration | 3 | Should Have | Backlog | Sprint 2 |
| **US-009** | Full Offline Map Tiles & Local Geofencing Cache | 8 | Could Have | Backlog | Sprint 2 |

**Tổng Story Points Backlog:** 42 Points  
**Cam kết Sprint 1 (MVP Walking Skeleton):** 26 Points (US-001 đến US-006)

---

## 2. CHI TIẾT USER STORIES (SPRINT 1 CANDIDATES)

### US-001: Khởi tạo Kiến trúc Lõi, Docker Container & Day-1 Observability
- **Mô tả:** Là kỹ sư triển khai, tôi muốn có hạ tầng Backend FastAPI chuẩn Clean Layered kèm Docker Compose, Structured JSON Logging và endpoint Health Check để hệ thống có thể khởi động 1-click an toàn và theo dõi trạng thái tức thời.
- **Story Points:** 3 | **Độ ưu tiên:** Must Have
- **Acceptance Criteria (AC):**
  - [ ] AC-1: Endpoint `GET /api/v1/health` trả về HTTP 200 `{ "status": "ok", "version": "1.0.0" }`.
  - [ ] AC-2: Hệ thống ghi log dạng Structured JSON kèm trường `timestamp`, `level`, `correlation_id` và `message`.
  - [ ] AC-3: Tập lệnh `run.bat` (Windows) và `run.sh` (Linux) kiểm tra môi trường, sinh secret an toàn và khởi chạy thành công trong vòng dưới 45 giây.

---

### US-002: Động Cơ Không Gian & Cảnh Báo Điểm Đen Giao Thông
- **Mô tả:** Là người đi xe máy, tôi muốn nhận được cảnh báo âm thanh trước 150m - 300m khi di chuyển tới gần camera phạt nguội hoặc điểm ngập úng để tôi chủ động giảm tốc độ hoặc đổi hướng an toàn.
- **Story Points:** 5 | **Độ ưu tiên:** Must Have
- **Acceptance Criteria (AC):**
  - [ ] AC-1: API `GET /api/v1/hazards` trả về đầy đủ danh sách điểm đen mẫu chuẩn GeoJSON tại TP.HCM và Hà Nội (gồm camera phạt nguội, điểm ngập nước, giới hạn tốc độ).
  - [ ] AC-2: API `POST /api/v1/hazards/check-proximity` tính toán chính xác khoảng cách Haversine giữa vị trí người dùng và các điểm đen; trả về cờ cảnh báo `has_alert: true` khi khoảng cách $\le$ bán kính cho phép.
  - [ ] AC-3: Mỗi cảnh báo trả về chuỗi văn bản mẫu `speech_announcement` bằng tiếng Việt rõ ràng, ngắn gọn để phát qua loa/tai nghe (ví dụ: "Chú ý: Phía trước 180 mét có camera phạt nguội tốc độ 50 km/h").

---

### US-003: Lộ Trình Xe Máy Thông Minh & Né Tránh Vùng Nguy Hiểm
- **Mô tả:** Là người điều khiển xe máy, tôi muốn hệ thống tính toán tuyến đường tối ưu từ tọa độ bắt đầu đến đích đến, tự động phát hiện và đánh dấu các điểm nguy hiểm trên cung đường để tránh rủi ro.
- **Story Points:** 5 | **Độ ưu tiên:** Must Have
- **Acceptance Criteria (AC):**
  - [ ] AC-1: API `POST /api/v1/routes/directions` tính toán khoảng cách (km), thời gian ước tính (phút) và danh sách tọa độ polyline lộ trình xe máy.
  - [ ] AC-2: Hệ thống quét toàn bộ các điểm cảnh báo nằm dọc theo hành lang tuyến đường (buffer 50m) và trả về danh sách `hazards_on_route`.
  - [ ] AC-3: Khi bật tùy chọn `avoid_floods = true`, hệ thống ưu tiên lộ trình an toàn không cắt qua các điểm ngập nước nghiêm trọng. Tích hợp sẵn thuật toán heuristic fallback khi không có kết nối OSRM bên ngoài.

---

### US-004: Trợ Lý Giọng Nói Rảnh Tay & Bộ Não NLP Phân Loại Ý Định
- **Mô tả:** Là người đi xe máy đang lái xe trên đường, tôi muốn có thể ra lệnh bằng giọng nói tiếng Việt ("Chỉ đường tới Chợ Bến Thành", "Phía trước có camera không?", "Đường này có ngập không?") để trợ lý tự động phản hồi qua âm thanh mà tôi không cần buông tay lái.
- **Story Points:** 5 | **Độ ưu tiên:** Must Have
- **Acceptance Criteria (AC):**
  - [ ] AC-1: Client Web/PWA tích hợp Web Speech Recognition tiếng Việt `vi-VN` với phím Micro HUD kích thước lớn và cơ chế tự động kích hoạt sau khi ra lệnh.
  - [ ] AC-2: API `POST /api/v1/voice/parse` phân loại chính xác các Intent cốt lõi (`NAVIGATE`, `CHECK_HAZARDS`, `CHECK_FLOOD_WEATHER`, `REPORT_INCIDENT`, `HELP_GUIDE`) với độ chính xác đạt $\ge 90\%$.
  - [ ] AC-3: Trích xuất chính xác thực thể điểm đến (Destination) từ các mẫu câu tự nhiên tiếng Việt và sinh câu thoại phản hồi `voice_response` thân thiện.

---

### US-005: Giao Diện Người Dùng PWA Mobile-First Song Ngữ & Chế Độ Lái Ban Đêm
- **Mô tả:** Là người dùng xe máy, tôi muốn một giao diện Web/PWA trực quan, tối ưu cho màn hình điện thoại gắn trên xe máy, hỗ trợ chuyển đổi song ngữ (EN/VI), bản đồ Leaflet mượt mà, và chế độ HUD ban đêm độ tương phản cao để nhìn rõ dưới trời nắng hoặc đêm tối.
- **Story Points:** 5 | **Độ ưu tiên:** Must Have
- **Acceptance Criteria (AC):**
  - [ ] AC-1: Giao diện hỗ trợ chuyển đổi mượt mà 2 ngôn ngữ: Tiếng Anh (`en`) và Tiếng Việt (`vi`) qua nút chuyển đổi (**Language Switcher: EN | VI**) trên Header; văn bản quản lý qua `locales/en.json` và `locales/vi.json`, lưu trạng thái vào `localStorage`.
  - [ ] AC-2: Bản đồ Leaflet.js tương tác hiển thị vị trí người dùng, lộ trình xe máy và các marker biểu tượng cảnh báo rõ ràng (Camera màu đỏ, Điểm ngập màu xanh dương, Giới hạn tốc độ màu vàng).
  - [ ] AC-3: Chế độ HUD Mode với các nút thao tác nhanh siêu to, hỗ trợ nút bấm bằng ngón tay cái khi đeo găng tay xe máy, hiển thị tốc độ hiện tại và cảnh báo nhấp nháy khi có nguy hiểm.

---

### US-006: Trang Chuyên Biệt Quản Lý Huấn Luyện & Tinh Chỉnh Mô Hình (Model Training Page)
- **Mô tả:** Là kỹ sư AI / Quản trị viên hệ thống, tôi muốn có một trang chuyên biệt (`/training.html`) để giám sát dữ liệu mẫu, theo dõi chỉ số mô hình NLP, và có thể tinh chỉnh siêu tham số (Hyperparameters, Epochs, Learning Rate, Architecture) và kích hoạt huấn luyện không đồng bộ.
- **Story Points:** 3 | **Độ ưu tiên:** Must Have
- **Acceptance Criteria (AC):**
  - [ ] AC-1: Có liên kết truy cập trang Quản lý Huấn luyện từ Navbar chính; giao diện hỗ trợ song ngữ EN/VI.
  - [ ] AC-2: Hiển thị đầy đủ 4 nhóm thông số: (A) Dataset & Môi trường, (B) Siêu tham số cơ bản (Epochs, Batch size, Learning rate), (C) Kiến trúc mô hình (TF-IDF Classifier, PEFT/LoRA Light, Heuristic), (D) Checkpoint & Metrics (Accuracy, F1-score).
  - [ ] AC-3: API `POST /api/v1/training/train` kích hoạt tiến trình huấn luyện nền mà không gây nghẽn Web thread chính; cập nhật trạng thái thời gian thực qua polling `/api/v1/training/status`.
