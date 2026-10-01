# ADR-003: Kiến Trúc Trợ Lý Giọng Nói Rảnh Tay & Bộ Phân Loại Ý Định Tiếng Việt

- **Ngày ban hành:** 2026-10-01
- **Trạng thái:** Accepted
- **Người đề xuất:** Architect (Sprint 0)
- **Các bên liên quan:** Coder, QA & Simulator, Security Auditor

---

## 1. Bối cảnh (Context & Problem Statement)
Người lái xe máy không thể bấm phím hay nhìn màn hình khi đang di chuyển trên đường. Hệ thống cần một cơ chế nhận diện giọng nói (STT) tiếng Việt và tổng hợp giọng nói phát âm (TTS) phản hồi bằng âm thanh qua tai nghe Bluetooth, kèm một bộ não hiểu ý định (NLP Intent Classifier) có thể xử lý các câu lệnh: tìm đường, hỏi camera phía trước, kiểm tra ngập nước, cảnh báo tốc độ, và báo cáo sự cố giao thông.

---

## 2. Các Phương Án Cân Nhắc (Options Considered)

| Phương án | Ưu điểm | Nhược điểm | Đánh giá |
|---|---|---|---|
| **Phương án 1 (Được chọn): Hybrid Edge-Speech + Server NLP Intent Engine** | Tận dụng Web Speech API chuẩn HTML5 chạy trực tiếp trên điện thoại: 0 độ trễ thu âm, hỗ trợ tốt tiếng Việt `vi-VN`. Backend xử lý phân loại Intent bằng Hybrid Rule-based + Vector/Regex Classifier với độ trễ < 30ms. Phản hồi bằng Web Speech Synthesis tiếng Việt. | Phụ thuộc vào quyền Microphone của trình duyệt Web. | **Khuyến nghị** |
| **Phương án 2: Streaming Raw Audio lên Server chạy OpenAI Whisper** | Độ nhận diện câu từ phức tạp cao. | Cần GPU mạnh trên server, băng thông 4G tốn kém, độ trễ 2-4 giây không đáp ứng được yêu cầu phản xạ giao thông tức thời. | Không chọn |
| **Phương án 3: Chỉ dùng phím bấm Touch UI** | Đơn giản khi lập trình. | Vi phạm nghiêm trọng mục tiêu an toàn của người đi xe máy (buộc người dùng phải nhìn và bấm màn hình). | Không chọn |

---

## 3. Quyết Định Được Chọn (Decision Outcome)
- **Quyết định:**
  - **Client-Side (PWA Frontend):**
    - `webkitSpeechRecognition` / `SpeechRecognition` với `lang = 'vi-VN'` (hoặc `en-US` theo ngôn ngữ đang chọn).
    - Hỗ trợ phím micro 1-chạm kích thước lớn (HUD Motorbike Mode) và chế độ tự động lắng nghe sau mỗi phát lệnh.
    - `window.speechSynthesis` đọc to các thông báo cảnh báo nguy hiểm (Voice TTS).
  - **Server-Side (FastAPI Application):**
    - `VoiceIntentService` phân tích câu lệnh tiếng Việt thành các Intents:
      1. `NAVIGATE`: Tìm đường tới địa điểm (trích xuất địa danh/đích đến).
      2. `CHECK_HAZARDS`: Hỏi camera, chốt kiểm tra, biển báo phía trước.
      3. `CHECK_FLOOD_WEATHER`: Hỏi tình trạng ngập nước, trời mưa.
      4. `REPORT_INCIDENT`: Báo cáo tắc đường hoặc tai nạn.
      5. `HELP_GUIDE`: Hướng dẫn sử dụng trợ lý rảnh tay.

---

## 4. Hậu Quả & Đánh Đổi (Consequences)
- **Tác động tích cực:** Tốc độ phản hồi cực nhanh (< 200ms tổng chu trình), hoạt động mượt mà trên Chrome Android và Safari iOS, tiết kiệm 100% chi phí API âm thanh bên thứ ba.
- **Tác động tiêu cực:** Cần xây dựng bộ từ khóa đồng nghĩa phong phú trong tiếng Việt (ví dụ: "chỉ đường tới", "dẫn đường ra", "đi đến", "phía trước có bắn tốc độ không", "đường này có ngập không").

---

## 5. Chỉ Dẫn Thực Thi Dành Cho Coder (Implementation Directive)
- Bước 1: Viết module `frontend/static/app.js` tích hợp Web Speech API (nhận diện liên tục, xử lý lỗi No-Speech, kết nối tai nghe Bluetooth).
- Bước 2: Viết module `backend/src/application/voice_intent_service.py` với bộ regex và token matcher hỗ trợ cả Tiếng Việt có dấu và không dấu.
- Bước 3: Tạo trang chuyên biệt `frontend/static/training.html` cho phép xem danh sách intent, kiểm tra độ chính xác, và tinh chỉnh siêu tham số mô hình.

---

## 6. Tiêu Chí Nghiệm Thu Cho QA (Verification Criteria)
- Gửi 20 câu lệnh giọng nói tiếng Việt mẫu vào API `/api/v1/voice/parse`. Tỷ lệ nhận diện đúng Intent và trích xuất điểm đến đạt $\ge 90\%$.
