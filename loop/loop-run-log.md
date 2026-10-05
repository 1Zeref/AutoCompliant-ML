# AutoCompliant-ML Loop Run Log

Nhật ký ghi lại chi tiết các chu kỳ chạy thực tế của AutoCompliant-ML Autonomous Engineering Loop.

---

## Log Entries

### [2026-10-05 17:34:48] Cycle #001 - Loop Engineering Architecture Setup
- **Loop**: Setup & Verification of Loop Engineering Architecture & CLI Tools
- **Tool Tested**: `loop-gate check`
- **Result**: `ALLOWED [ok]` (Exit Code 0)
- **Status**: PASSED

### [2026-10-05 17:42:00] Loop Planning
- **Action**: Chia tách `implementation_plan.md` thành 5 vòng lặp tự hành độc lập và đồng bộ `gate.yaml`.
- **Status**: PASSED

### [2026-10-05 17:48:10] Cycle #002 - Loop 1: Env & Config Schema
- **Actions Completed**: Cài đặt `uv`, khởi tạo `.venv`, Pydantic schema, YAML loader, `configs/bridge_amplifier.yaml`, `configs/scott_russell.yaml`.
- **Gate Result**: 5/5 passed.

### [2026-10-05 17:53:15] Cycle #003 - Loop 2: Data & Adaptive Preprocessor
- **Actions Completed**: `AdaptivePreprocessor`, `SyntheticCompliantGenerator`, `CompliantDataset`, kiểm tra không rò rỉ dữ liệu.
- **Gate Result**: 5/5 passed.

### [2026-10-05 17:58:30] Cycle #004 - Loop 3: Multi-Output Model Zoo
- **Actions Completed**: `MultiOutputGPR`, `XGBoostSurrogate`, `LightGBMSurrogate`, `RandomForestSurrogate`, `AdaptiveMLPSurrogate`, `PolynomialRSMSurrogate`.
- **Gate Result**: 4/4 passed ($R^2 \ge 0.90$).

### [2026-10-05 18:14:30] Cycle #005 - Loop 4: Benchmark & Evaluation Engine
- **Actions Completed**: `metrics.py`, `benchmark.py`, `run_benchmark.py`, xuất `reports/leaderboard.json` và `reports/leaderboard.md`.
- **Gate Result**: Top Model `GaussianProcessRegression` (Test $R^2 = 0.9970$).

### [2026-10-05 18:18:15] Cycle #006 - Loop 5: NSGA-II & MCDM Integration
- **Actions Completed**:
  - Cài đặt `pymoo==0.6.2`.
  - Xây dựng bài toán tối ưu hóa [autocompliant/optimization/problem.py](file:///d:/CODE/AutoCompliant-ML/autocompliant/optimization/problem.py).
  - Xây dựng bộ giải tiến hóa [autocompliant/optimization/nsga2_solver.py](file:///d:/CODE/AutoCompliant-ML/autocompliant/optimization/nsga2_solver.py).
  - Xây dựng thuật toán quyết định TOPSIS [autocompliant/optimization/mcdm.py](file:///d:/CODE/AutoCompliant-ML/autocompliant/optimization/mcdm.py).
  - Xây dựng CLI [run_optimization.py](file:///d:/CODE/AutoCompliant-ML/run_optimization.py).
  - Viết bộ kiểm thử [tests/test_optimization.py](file:///d:/CODE/AutoCompliant-ML/tests/test_optimization.py).
- **Gate Verification Results**:
  1. `pytest tests/test_optimization.py -v`: **3/3 PASSED (100%)**
  2. Toàn bộ test suite tích lũy `pytest tests/`: **19/19 PASSED (100%)**
  3. Tối ưu hóa thực tế qua CLI: Tìm được **72 nghiệm Pareto trong 0.24 giây**, xuất [reports/pareto_front.csv](file:///d:/CODE/AutoCompliant-ML/reports/pareto_front.csv).
  4. TOPSIS xác định cấu hình Knee-point: $t=0.3678\text{ mm}, w=14.9383\text{ mm}, l=39.3879\text{ mm}, \theta=7.0716^\circ, r=2.4905\text{ mm}$.
  5. Thỏa mãn 100% ràng buộc an toàn tĩnh $F_1 = 1.5002 \ge 1.50$.
  6. `tools\loop-gate.cmd check`: **ALLOWED [ok]** (Exit code 0).
- **Status**: PASSED

### [2026-10-05 18:28:40] Cycle #007 - Loop 6: WebUI Interface & End-to-End Pipeline
- **Actions Completed**:
  - Cài đặt thư viện Web: `fastapi`, `uvicorn`, `python-multipart`, `httpx`, `jinja2`.
  - Thiết kế kiến trúc Web Dashboard tích hợp tại [autocompliant/web/app.py](file:///d:/CODE/AutoCompliant-ML/autocompliant/web/app.py) và [web_app.py](file:///d:/CODE/AutoCompliant-ML/web_app.py).
  - Cung cấp toàn bộ REST API:
    - `GET /api/configs`: Liệt kê các topology configs.
    - `GET /api/config-details`: Chi tiết tham số $D_{\text{in}}, D_{\text{out}}$, bounds, constraints.
    - `POST /api/dataset/generate`: Sinh dữ liệu vật lý mô phỏng trực tiếp từ `SyntheticCompliantGenerator`.
    - `POST /api/dataset/upload`: Upload file CSV/Parquet và kiểm tra nghiêm ngặt tính hợp lệ của schema.
    - `POST /api/pipeline/run`: Kích hoạt pipeline khép kín (huấn luyện Model Zoo, so chuẩn $R^2$/RMSE/Latency, chạy NSGA-II giải nghiệm Pareto và tính điểm TOPSIS).
    - `GET /api/download/{filename}`: Download trực tiếp `pareto_front.csv`, `best_configuration.json`, `best_surrogate.pkl`.
  - Xây dựng giao diện Responsive Single Page Application (HTML5/CSS3/Vanilla JS + Chart.js) trực quan hóa đường biên Pareto và Knee-point.
  - Viết bộ kiểm thử toàn diện [tests/test_web.py](file:///d:/CODE/AutoCompliant-ML/tests/test_web.py).
  - Cập nhật Gatekeeper: Bổ sung `web_ui_gate` vào `gate.yaml` và `loop/gate.yaml`.
- **Gate Verification Results**:
  1. `pytest tests/test_web.py -v`: **6/6 PASSED (100%)**
  2. Toàn bộ test suite tích lũy `pytest tests/`: **25/25 PASSED (100%)**
  3. `tools\loop-gate.cmd check`: **ALLOWED [ok]** (Exit code 0).
- **Status**: PASSED

### [2026-10-05 19:50:00] Cycle #008 - WebUI Guided Stepper Wizard via FastAPI REST Architecture
- **Actions Completed**:
  - Triển khai kiến trúc **Session-based State Machine** và `SessionManager` tại [autocompliant/web/app.py](file:///d:/CODE/AutoCompliant-ML/autocompliant/web/app.py) lưu trữ tại `artifacts/sessions/{session_id}`.
  - Thiết lập cơ chế **Server-side Enforced Gate**: Kiểm tra nghiêm ngặt tính hoàn thiện của Bước $N-1$ trước khi cấp phép thực thi Bước $N$, trả về HTTP 400 và thông báo tiếng Việt trực quan.
  - Xây dựng trọn bộ REST API Stepper:
    - `GET /api/topologies`: Trả về schema chi tiết các topology, cận hình học, mục tiêu và ràng buộc.
    - `POST /api/wizard/step1-data`: Khởi tạo session, nạp synthetic hoặc file CSV/Parquet, kiểm tra schema, NaN/Null, kiểu số.
    - `POST /api/wizard/step2-train`: K-Fold Cross-Validation, so chuẩn 6 mô hình Model Zoo, trích xuất best surrogate model và dữ liệu biểu đồ phân tán Actual vs Predicted.
    - `POST /api/wizard/step3-optimize`: Chạy bài toán tối ưu đa mục tiêu NSGA-II, lọc mặt trước Pareto và xác định điểm thỏa hiệp tối ưu TOPSIS Knee-point.
    - `GET /api/wizard/step4-results`: Bảng tổng kết cấu hình tối ưu và đường dẫn tải tệp.
    - Bộ tải tệp: `/api/wizard/download/pareto-csv`, `/api/wizard/download/best-design-json`, `/api/wizard/download/model-pkl`.
  - Xây dựng giao diện Frontend Single-Page Stepper Wizard hiện đại tại [autocompliant/web/templates/index.html](file:///d:/CODE/AutoCompliant-ML/autocompliant/web/templates/index.html) (Tailwind CSS + Plotly.js + Chart.js):
    - Stepper Navigation Bar 4 bước với trạng thái khóa/mở tự động.
    - Biểu đồ phân tán 2D tương tác Plotly.js ($F_2$ vs $f$, màu sắc theo $F_1$, tooltip chi tiết, ngôi sao ⭐ TOPSIS Knee-point).
    - Biểu đồ Actual vs Predicted scatter plot kiểm định mô hình tốt nhất.
    - Spinner / Loading Banner với ước tính thời gian thực thi.
  - Viết bộ test tự động nâng cao [tests/test_web.py](file:///d:/CODE/AutoCompliant-ML/tests/test_web.py) với 13 bài test kiểm thử toàn diện cả luồng tuần tự và các kịch bản nhảy cóc, thiếu cột dữ liệu.
- **Gate Verification Results**:
  1. `pytest tests/test_web.py -v`: **13/13 PASSED (100%)**
  2. Toàn bộ test suite tích lũy `pytest tests/`: **32/32 PASSED (100%)**
  3. `tools\loop-gate.cmd check`: **ALLOWED [ok]** (Exit code 0).
- **Status**: 🏁 **GUIDED STEPPER WIZARD FULLY OPERATIONAL & VERIFIED.**
