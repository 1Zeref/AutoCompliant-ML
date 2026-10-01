# Vietnam Motorbike Smart Traffic Assistant
## Trợ Lý Điều Hướng & Cảnh Báo An Toàn Giao Thông Rảnh Tay Cho Người Đi Xe Máy

[![CI/CD Pipeline](https://github.com/example/traffic-assistant/actions/workflows/deploy.yml/badge.svg)](.github/workflows/deploy.yml)
[![Coverage](https://img.shields.io/badge/Coverage-86%25-brightgreen.svg)](tests/)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](docker-compose.yml)

---

## 1. Giới Thiệu Tổng Quan
Hệ thống **Vietnam Motorbike Smart Traffic Assistant** là ứng dụng Web/PWA rảnh tay đầu tiên được thiết kế chuyên biệt cho văn hóa giao thông xe máy tại đô thị Việt Nam (TP.HCM, Hà Nội):
- **Tương tác giọng nói tiếng Việt rảnh tay (Hands-Free Voice AI):** Nhận diện lệnh giọng nói qua tai nghe Bluetooth (Web Speech API) và phân loại ý định qua NLP Intent Engine với độ trễ < 30ms.
- **Cảnh báo điểm đen thời gian thực (Spatial Hazard Alerting):** Tự động phát âm thanh cảnh báo trước 150m - 300m khi sắp tiếp cận camera phạt nguội, điểm đen ngập úng triều cường/mùa mưa, và đoạn đường giới hạn tốc độ theo làn.
- **Định tuyến xe máy thông minh (Motorbike Route Engine):** Tích hợp OpenStreetMap và OSRM, tự động quét hành lang tuyến đường và chủ động né tránh các điểm ngập sâu khi có mưa lớn.
- **Chế độ lái xe máy ban đêm (High-Contrast Motorbike HUD Mode):** Hiển thị tốc độ lớn, trạng thái an toàn màu sắc trực quan, và các nút bấm một chạm siêu to thao tác dễ dàng khi đeo găng tay xe máy.
- **Trang Quản trị & Huấn luyện Mô hình AI Chuyên biệt (`/training.html`):** Giám sát dataset, cấu hình 4 nhóm siêu tham số (Epochs, LR, PEFT/LoRA Rank, Checkpoint Strategy) và huấn luyện nền thời gian thực.
- **Đa ngôn ngữ toàn diện (Bilingual i18n):** Hỗ trợ chuyển đổi nhanh giữa Tiếng Việt (`vi`) và Tiếng Anh (`en`).

---

## 2. Khởi Chạy 1-Click (1-Click Run)

### Trên Windows
Nhấp đúp chuột vào file hoặc chạy từ CMD / PowerShell:
```cmd
run.bat
```

### Trên Linux / macOS
Cấp quyền thực thi và chạy:
```bash
chmod +x run.sh
./run.sh
```

### Chạy Cục Bộ Không Dùng Docker (Local Dev)
```bash
pip install -r backend/requirements.txt
python -m uvicorn backend.src.presentation.main:app --reload --port 8000
```

---

## 3. Đường Dẫn Truy Cập Hệ Thống
Sau khi khởi động, truy cập các địa chỉ sau trên trình duyệt:
- **Giao diện PWA & HUD Lái Xe Máy:** [http://localhost:8000](http://localhost:8000)
- **Trang Quản Trị & Huấn Luyện AI:** [http://localhost:8000/training.html](http://localhost:8000/training.html)
- **Tài liệu Tương tác API (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check & Readiness Endpoint:** [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

## 4. Chạy Kiểm Thử TDD & Coverage
```bash
# Chạy toàn bộ 17 unit & integration tests
pytest tests/

# Kiểm tra độ phủ mã nguồn (Code Coverage >= 80%)
pytest --cov=backend/src tests/
```

---

## 5. Cấu Trúc Thư Mục
Dự án được tổ chức theo kiến trúc **Clean Layered Architecture**:
```
traffic-assistant/
├── backend/
│   └── src/
│       ├── core/           # Config, Structured JSON Logger, Middleware
│       ├── domain/         # Schemas & Entities (Hazard, Route, Voice, Training)
│       ├── infrastructure/ # Repositories, Seed Data, OSRM Client
│       ├── application/    # Services (HazardService, RoutingService, VoiceIntentService, TrainingService)
│       └── presentation/   # FastAPI Router (api_v1.py) & Entrypoint (main.py)
├── frontend/
│   ├── index.html          # PWA Client, Bản đồ Leaflet, Chế độ Lái HUD
│   ├── locales/            # Từ điển i18n song ngữ (vi.json & en.json)
│   └── static/             # styles.css, app.js, training.html, training.js
├── docs/                   # Tài liệu kiến trúc, ADRs, Scrum Backlogs, Handoff Reports
└── tests/                  # Bộ kiểm thử TDD (test_hazard, test_routing, test_voice, test_api)
```
