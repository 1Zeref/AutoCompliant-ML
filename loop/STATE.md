# Current Loop State

## Overall Status: 🟢 ALL 6 AUTONOMOUS LOOPS COMPLETED & VERIFIED
- **Active Goal**: Toàn bộ hệ thống AutoCompliant-ML (Core AI + WebUI Pipeline) đã hoàn thành, kiểm thử và nghiệm thu thành công.
- **Repository Branch**: `main`

---

## 6 Autonomous Loops Summary

### ✅ Loop 1: Environment & Config Schema (Cycle #002) - COMPLETED
- Khởi tạo môi trường ảo Python 3.11 (`.venv`), Pydantic schema, YAML loader cho `configs/bridge_amplifier.yaml` và `configs/scott_russell.yaml`.
- **Gate 1**: `pytest tests/test_config.py -v` $\rightarrow$ **5/5 PASSED (100%)**.

### ✅ Loop 2: Data & Adaptive Preprocessor (Cycle #003) - COMPLETED
- Xây dựng `AdaptivePreprocessor` độc lập X/Y, `SyntheticCompliantGenerator`, `CompliantDataset` chống rò rỉ dữ liệu triệt để.
- **Gate 2**: `pytest tests/test_data.py -v` $\rightarrow$ **5/5 PASSED (100%)**, `test_no_data_leakage` PASSED.

### ✅ Loop 3: Multi-Output Model Zoo (Cycle #004) - COMPLETED
- Triển khai Model Zoo: `BaseSurrogateModel`, `MultiOutputGPR` (với Bayesian Uncertainty $\sigma(X)$), `XGBoostSurrogate`, `LightGBMSurrogate`, `RandomForestSurrogate`, `AdaptiveMLPSurrogate` (PyTorch Tabular Net), `PolynomialRSMSurrogate`.
- **Gate 3**: `pytest tests/test_models.py -v` $\rightarrow$ **4/4 PASSED (100%)**, $R^2 \ge 0.90$.

### ✅ Loop 4: Benchmark & Evaluation Engine (Cycle #005) - COMPLETED
- Triển khai động cơ tính toán đa chỉ số ($R^2$, RMSE, MAE, MAPE), $K$-Fold Cross Validation ($k=5$), đo độ trễ suy luận latency (ms/1k), CLI `run_benchmark.py` xuất Leaderboard JSON & Markdown.
- **Gate 4**: `python run_benchmark.py --config configs/bridge_amplifier.yaml --check` $\rightarrow$ **PASSED**.
  - Top Model: `GaussianProcessRegression` (Test $R^2 = 0.9970$, CV $R^2 = 0.9969 \pm 0.0008$, Latency: 23.42 ms / 1k).
  - Artifacts: `models/artifacts/best_surrogate.pkl`, `reports/leaderboard.json`, `reports/leaderboard.md`.

### ✅ Loop 5: NSGA-II & MCDM Integration (Cycle #006) - COMPLETED
- Tích hợp `pymoo`: `CompliantMechanismProblem`, thuật toán tiến hóa `NSGA2Solver` đánh giá song song theo batch, phương pháp ra quyết định đa tiêu chí `topsis_select_best_tradeoff` chọn nghiệm Knee-point tối ưu.
- CLI: `run_optimization.py` tối ưu hóa đa mục tiêu trong **0.24 giây**, tìm ra **72 nghiệm Pareto**, xuất `reports/pareto_front.csv`.
- **Gate 5**: `pytest tests/test_optimization.py -v` $\rightarrow$ **3/3 PASSED (100%)**, ràng buộc $F_1 \ge 1.5$ được thỏa mãn nghiêm ngặt.

### ✅ Loop 6: WebUI Interface & End-to-End Pipeline (Cycle #007) - COMPLETED
- Xây dựng ứng dụng web hiện đại FastAPI + SPA:
  - Giao diện chọn topology config (`configs/bridge_amplifier.yaml`, `configs/scott_russell.yaml`).
  - Hỗ trợ tải file dataset (`.csv`) hoặc sinh tức thì `SyntheticCompliantGenerator`, kèm bảng Data Preview & kiểm tra tính hợp lệ của $D_{\text{in}}, D_{\text{out}}$.
  - Nút bấm kích hoạt huấn luyện/so chuẩn mô hình surrogate và tối ưu hóa đa mục tiêu NSGA-II kèm tùy biến `pop_size`, `generations`.
  - Hiển thị bảng Leaderboard, biểu đồ Pareto Frontier 2D trực quan kèm điểm tối ưu TOPSIS (Knee-point) với Chart.js.
  - Tải xuống kết quả: `pareto_front.csv`, `best_configuration.json`, `best_surrogate.pkl`.
- Tích hợp launcher: `python web_app.py --port 8000`.
- **Gate 6**: `pytest tests/test_web.py -v` $\rightarrow$ **6/6 PASSED (100%)**.

### ✅ Loop 7: WebUI Guided Stepper Wizard (Cycle #008) - COMPLETED
- Nâng cấp kiến trúc WebUI theo nguyên tắc **Session-based State Machine**:
  - `SessionManager` lưu cache phiên làm việc độc lập trong bộ nhớ và thư mục `artifacts/sessions/{session_id}`.
  - Rào chắn bảo vệ phía máy chủ (Server-side Enforced Gate): Chặn các request nhảy cóc khi bước trước chưa hoàn thành (HTTP 400 kèm thông báo tiếng Việt chi tiết).
  - Khởi tạo API RESTful dạng Stepper 4 bước:
    - `GET /api/topologies`: Trả về schema chi tiết các topology, cận hình học, mục tiêu và ràng buộc.
    - `POST /api/wizard/step1-data`: Khởi tạo session, nạp synthetic hoặc file CSV/Parquet, kiểm tra schema, NaN/Null, kiểu số.
    - `POST /api/wizard/step2-train`: K-Fold Cross-Validation, so chuẩn 6 mô hình Model Zoo, trích xuất best surrogate model và dữ liệu biểu đồ phân tán Actual vs Predicted.
    - `POST /api/wizard/step3-optimize`: Chạy bài toán tối ưu đa mục tiêu NSGA-II, lọc mặt trước Pareto và xác định điểm thỏa hiệp tối ưu TOPSIS Knee-point.
    - `GET /api/wizard/step4-results`: Bảng tổng kết cấu hình tối ưu và đường dẫn tải tệp.
    - Bộ tải tệp: `/api/wizard/download/pareto-csv`, `/api/wizard/download/best-design-json`, `/api/wizard/download/model-pkl`.
  - Frontend Single-Page Application (HTML5 + Tailwind CSS + Plotly.js + Chart.js) tại [autocompliant/web/templates/index.html](file:///d:/CODE/AutoCompliant-ML/autocompliant/web/templates/index.html):
    - Thanh tiến trình Stepper 4 bước với cơ chế khóa bước chưa mở.
    - Biểu đồ phân tán 2D tương tác Plotly.js ($F_2$ vs $f$, tô màu theo $F_1$, gắn nhãn tooltip) và ngôi sao vàng tại điểm TOPSIS Knee-point.
    - Spinner / Loading Banner kèm thông báo trạng thái tức thời.
- **Gate 7**: `pytest tests/test_web.py -v` $\rightarrow$ **13/13 PASSED (100%)**, toàn bộ test suite `pytest tests/ -v` $\rightarrow$ **32/32 PASSED (100%)**.

### ✅ Loop 8: Dynamic Topology Selection & Column Role Mapping (Cycle #009) - COMPLETED
- Triển khai tính năng **Dynamic Topology Selection** cho phép tự động nhận diện cấu trúc dataset từ tệp CSV bất kỳ và gán vai trò trực tiếp trên giao diện:
  - Pydantic Models: `ColumnMapping` (name, role: input/output/ignore, objective: max/min, bounds, constraints) và `DynamicConfigRequest`.
  - Backend Endpoints:
    - `POST /api/wizard/parse-columns`: Đọc CSV, kiểm tra kiểu dữ liệu số, tính toán miền giá trị `[min, max]` của từng cột, tạo session và trả về 5 dòng preview.
    - `POST /api/wizard/configure-topology`: Khởi tạo động đối tượng `TopologyConfig`, lưu `topology.yaml` trong thư mục session, khởi tạo `CompliantDataset` và mở khóa Bước 2. Bắt buộc kiểm tra ít nhất 1 biến Input và 1 biến Output.
  - Frontend SPA tại [autocompliant/web/templates/index.html](file:///d:/CODE/AutoCompliant-ML/autocompliant/web/templates/index.html):
    - Pha 1 (Upload Area): Chọn file CSV bất kỳ, tự động gửi parse cột.
    - Pha 2 (Column Mapping Table): Bảng phân loại vai trò trực quan, hỗ trợ chọn `Input`, `Output`, `Ignore`, hướng tối ưu `Maximize/Minimize`, ngưỡng ràng buộc $\ge \text{min}, \le \text{max}$. Tự động vô hiệu hóa các ô không cần thiết khi chọn `Input` hoặc `Ignore`.
    - Hỗ trợ xem trước 5 dòng dữ liệu và nút bấm chuyển bước mượt mà.
- **Gate 8**: `pytest tests/test_web.py -v` $\rightarrow$ **16/16 PASSED (100%)**, toàn bộ test suite `pytest tests/ -v` $\rightarrow$ **35/35 PASSED (100%)**.

### ✅ Loop 9: Precision & Robustness Enhancement (Cycle #010) - COMPLETED
- Triển khai toàn diện 4 cơ chế nâng cao độ chuẩn xác, độ bền vững và tin cậy của hệ thống:
  1. **Outlier Detection & Cleaning (`filter_outliers`)**: Tích hợp thuật toán IQR và Z-Score lọc các điểm dị biệt hoặc lỗi phân kỳ/méo lưới FEA trong `autocompliant/data/preprocessor.py`.
  2. **Weighted Ensemble Surrogate (`WeightedEnsembleSurrogate`)**: Kết hợp các mô hình surrogate theo trọng số $w_m \propto \frac{R^2_m}{1 - R^2_m + \epsilon}$ và định lượng độ bất định nhận thức (Epistemic Uncertainty) $\sigma(x)$ từ độ phân kỳ giữa các thành viên.
  3. **Uncertainty-Aware Robust Optimization**: Hỗ trợ phạt độ bất định LCB ($\mu \mp \beta\sigma$) và thắt chặt ràng buộc an toàn kỹ thuật trong `CompliantMechanismProblem`.
  4. **Extrapolation Risk & Confidence Metric**: Đo lường khoảng cách chuẩn hóa (Mahalanobis/Z-score) từ điểm thiết kế Pareto tới không gian phân bố huấn luyện thực tế, gán nhãn độ tin cậy và cấp độ rủi ro ngoại suy.
  5. **WebUI & API Integration**: Bổ sung checkbox phạt độ bất định tại Bước 3 và hiển thị thẻ phân loại độ tin cậy (Confidence Badge) tại Bước 4.
- **Gate 9**: `pytest tests/test_precision.py -v` $\rightarrow$ **5/5 PASSED (100%)**, toàn bộ test suite `pytest tests/ -v` $\rightarrow$ **40/40 PASSED (100%)**.

### ✅ Loop 10: TOPSIS Degeneracy Resolution & Custom Bounds Input (Cycle #011) - COMPLETED
- Khắc phục triệt để lỗi `TOPSIS Relative Closeness: 0.0000` và hoàn thiện logic rủi ro ngoại suy:
  1. **TOPSIS Degeneracy Fix (`autocompliant/optimization/mcdm.py`)**:
     - Xử lý trường hợp tập Pareto suy biến về 1 nghiệm hoặc các nghiệm có cùng giá trị hàm mục tiêu ($d^+ + d^- = 0$): tự động chuẩn hóa $C_i = 1.0$ (thay vì $0.0000$).
  2. **Preserve Constrained Outputs in Pareto Front (`autocompliant/optimization/problem.py`)**:
     - Cập nhật logic `obj_indices`: Giữ lại các biến Output có đặt ràng buộc $\ge \text{min}$ hoặc $\le \text{max}$ trong danh sách hàm mục tiêu đa biến để NSGA-II luôn giải bài toán Pareto đa mục tiêu thực thụ, tránh biến thành bài toán đơn mục tiêu suy biến.
  3. **Custom Variable Bounds in Step 1 (`autocompliant/web/app.py` & `index.html`)**:
     - Mở rộng `ColumnMapping` với `bound_min` và `bound_max`.
     - Cho phép người dùng chỉnh sửa trực tiếp cận biến hình học $X_{\min}, X_{\max}$ tại Bước 1 (ví dụ: ép $D \in [0.55, 0.60]$, $E \in [45, 50]$ theo đúng bài báo thay vì dạt lên $[0.55, 0.65]$).
  4. **Refined Extrapolation Thresholds & Labels**:
     - Ngưỡng phân loại $z \le 1.5$ (Cao), $1.5 < z \le 2.0$ (Trung bình), $z > 2.0$ (Độ tin cậy thấp / Rủi ro ngoại suy cao).
- **Gate 10**: `pytest tests/ -v` $\rightarrow$ **40/40 PASSED (100%)**.

### ✅ Loop 11: Production Containerization & Docker Architecture (Cycle #012) - COMPLETED
- Triển khai toàn bộ giải pháp Docker hóa cho toàn bộ hệ thống AutoCompliant-ML:
  1. **Tệp `requirements.txt` cập nhật đầy đủ**: Bổ sung các thư viện ML (`xgboost`, `lightgbm`, `torch`), tối ưu hóa đa mục tiêu (`pymoo`), và web dashboard (`fastapi`, `uvicorn`, `python-multipart`, `jinja2`).
  2. **Tệp `Dockerfile` đa môi trường (Hybrid Environment)**: Sử dụng base image `python:3.11-slim`, cài đặt thư viện hệ thống C/C++ runtime (`libgomp1`, `build-essential`), tích hợp Node.js 18 LTS cho các công cụ audit/loop-gate, và chạy trực tiếp Web Dashboard trên port 8000.
  3. **Tệp `docker-compose.yml` phân chia microservices & batch jobs**:
     - `web`: Dịch vụ máy chủ FastAPI Stepper Wizard (`ports: 8000:8000`, volume mounts: `artifacts/`, `reports/`, `models/artifacts/`, `configs/`).
     - `optimizer`: Tác vụ ngầm tối ưu hóa NSGA-II + TOPSIS (`run_optimization.py`, profile `jobs`).
     - `benchmark`: Tác vụ ngầm so chuẩn mô hình surrogate Model Zoo (`run_benchmark.py`, profile `jobs`).
  4. **Tệp `.dockerignore` tinh gọn**: Loại bỏ triệt để file rác, virtual environment `.venv/`, `.git/`, `node_modules/`, và các file session tạm.
- **Gate 11**: `pytest tests/ -v` $\rightarrow$ **40/40 PASSED (100%)**, `loop-gate check` $\rightarrow$ **ALLOWED [ok]**.

---

## Cumulative Verification Status
- **Total Test Cases**: 40/40 PASSED (100%).
- **Policy Gatekeeper (`loop-gate`)**: 100% Policy Compliant (`ALLOWED [ok]`).
- **Optimal Mechanical Design Discovered**:
  - Hinge Thickness $t = 0.3678\text{ mm}$
  - Hinge Width $w = 14.9383\text{ mm}$
  - Arm Length $l = 39.3879\text{ mm}$
  - Bridge Angle $\theta = 7.0716^\circ$
  - Fillet Radius $r = 2.4905\text{ mm}$
  - Phản ứng cơ học: Hệ số an toàn $F_1 = 1.5002 \ge 1.50$, Chuyển vị $\Delta_{\text{out}} = 78.11\,\mu\text{m}$ (khuếch đại $7.8\times$), Tần số riêng $f = 754.96\text{ Hz}$.
