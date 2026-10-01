# SỔ TAY VẬN HÀNH HỆ THỐNG (OPERATIONS RUNBOOK)
## VIETNAM MOTORBIKE SMART TRAFFIC ASSISTANT

> **Phiên bản:** `1.0.0` | **Tác giả:** Trụ cột 5 — Report Scribe  
> **Trạng thái:** Production Ready

---

## 1. GIÁM SÁT HỆ THỐNG & HEALTH CHECK (MONITORING & OBSERVABILITY)

### 1.1 Endpoint Giám Sát Sẵn Sàng (Readiness & Liveness Probe)
- **URL:** `http://localhost:8000/api/v1/health`
- **Phương thức:** `GET`
- **Mẫu phản hồi kỳ vọng (HTTP 200 OK):**
  ```json
  {
    "status": "ok",
    "app_name": "Vietnam Motorbike Smart Traffic Assistant",
    "env": "production",
    "version": "1.0.0",
    "timestamp": "2026-10-01T20:45:00Z"
  }
  ```
- **Tiêu chuẩn cảnh báo (Alerting Threshold):**
  - Cảnh báo nếu HTTP Status $\neq 200$ trong 3 lần liên tiếp (mỗi lần cách nhau 10 giây).
  - Cảnh báo nếu thời gian phản hồi p95 $> 200\text{ ms}$.

### 1.2 Chính Sách Log Rotation (Chống Tràn Ổ Đĩa)
Cấu hình Docker Logging Driver trong file `/etc/docker/daemon.json` hoặc trong service compose:
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}
```

---

## 2. KẾ HOẠCH SAO LƯU DỮ LIỆU (BACKUP & RECOVERY PLAN)

### 2.1 Kịch Bản Sao Lưu Dữ Liệu Tự Động (Cron Job Hằng Ngày Lúc 2:00 AM)
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/traffic-assistant"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Sao lưu file seed data và model checkpoints
tar -czf "$BACKUP_DIR/backup_traffic_$TIMESTAMP.tar.gz" backend/src/infrastructure/seed_data.py

# Giữ lại tối đa 7 bản sao lưu gần nhất (Xóa bản cũ hơn 7 ngày)
find "$BACKUP_DIR" -type f -name "backup_traffic_*.tar.gz" -mtime +7 -delete
```

### 2.2 Quy Trình Phục Hồi Dữ Liệu Từ Bản Sao Lưu (Restore Procedure)
1. Dừng container: `docker compose down`
2. Giải nén bản sao lưu được chỉ định:
   ```bash
   tar -xzf /var/backups/traffic-assistant/backup_traffic_YYYYMMDD_HHMMSS.tar.gz -C /
   ```
3. Khởi động lại dịch vụ: `docker compose up -d`
4. Kiểm tra endpoint health: `curl -f http://localhost:8000/api/v1/health`

---

## 3. QUY TRÌNH HOÀN NGUYÊN KHẨN CẤP (ZERO-DOWNTIME ROLLBACK RUNBOOK)

Khi phát hiện sự cố nghiêm trọng trên môi trường Production sau khi cập nhật phiên bản mới:

1. **Bước 1 — Rollback mã nguồn về checkpoint ổn định gần nhất:**
   ```bash
   git checkout sprint-1-start
   ```
2. **Bước 2 — Khởi động lại containers từ image đã kiểm định:**
   ```bash
   docker compose down
   docker compose up -d --build
   ```
3. **Bước 3 — Xác nhận hệ thống hoạt động bình thường:**
   ```bash
   curl -f http://localhost:8000/api/v1/health
   ```

---

## 4. QUY TRÌNH VÁ LỖI NÓNG TRÊN PRODUCTION (HOTFIX PROTOCOL)

Khi phát sinh lỗi bảo mật hoặc bug khẩn cấp cần vá trực tiếp trên Production:

1. **Tạo nhánh hotfix từ nhánh production `main`:**
   ```bash
   git checkout main
   git checkout -b hotfix/fix-camera-geofence-leak
   ```
2. **Tiến hành sửa lỗi và viết regression test (Prove-It Pattern):**
   ```bash
   pytest tests/
   ```
3. **Commit và gắn thẻ phiên bản mới:**
   ```bash
   git commit -m "security(hotfix): patch proximity distance validation bug"
   git checkout main
   git merge --no-ff hotfix/fix-camera-geofence-leak
   git tag v1.0.1
   ```
4. **Đồng bộ về nhánh `develop` để tránh trôi code:**
   ```bash
   git checkout develop
   git merge --no-ff hotfix/fix-camera-geofence-leak
   ```
5. **Triển khai phiên bản vá lỗi:**
   ```cmd
   run.bat
   ```
