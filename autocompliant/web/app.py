"""FastAPI Web Application and Guided Stepper Wizard REST API for AutoCompliant-ML."""

import io
import json
import pickle
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Literal
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from autocompliant.config.loader import load_topology_config
from autocompliant.config.schema import TopologyConfig
from autocompliant.data.dataset import CompliantDataset
from autocompliant.data.preprocessor import AdaptivePreprocessor
from autocompliant.data.synthetic_generator import SyntheticCompliantGenerator
from autocompliant.evaluation.benchmark import ModelBenchmarkEngine, BenchmarkResult
from autocompliant.optimization.problem import CompliantMechanismProblem
from autocompliant.optimization.nsga2_solver import NSGA2Solver, OptimizationResult
from autocompliant.optimization.mcdm import topsis_select_best_tradeoff
from autocompliant.models.base import BaseSurrogateModel
from autocompliant.models import (
    PolynomialRSMSurrogate,
    RandomForestSurrogate,
    XGBoostSurrogate,
    LightGBMSurrogate,
    AdaptiveMLPSurrogate,
    MultiOutputGPR,
)

app = FastAPI(
    title="AutoCompliant-ML WebUI",
    description="Config-driven Machine Learning & NSGA-II Optimization Dashboard for Compliant Mechanisms",
    version="2.0.0",
)


# ==============================================================================
# 1. Pydantic Request & Response Schemas
# ==============================================================================

class Step2Request(BaseModel):
    session_id: str = Field(..., description="ID của phiên làm việc từ Bước 1")
    cv_folds: int = Field(default=5, ge=2, le=10, description="Số fold Cross-Validation")
    scaler_type: Literal["standard", "minmax", "robust"] = Field(
        default="standard", description="Thuật toán chuẩn hóa dữ liệu"
    )


class Step3Request(BaseModel):
    session_id: str = Field(..., description="ID của phiên làm việc từ Bước 2")
    pop_size: int = Field(default=80, ge=20, le=500, description="Kích thước quần thể NSGA-II")
    generations: int = Field(default=50, ge=10, le=500, description="Số thế hệ tiến hóa")
    selected_model: Optional[str] = Field(
        default=None, description="Tên mô hình surrogate muốn sử dụng (mặc định: best model)"
    )


# ==============================================================================
# 2. Session Management & Server-side Enforced Gate
# ==============================================================================

class SessionState:
    """Manages server-side state machine for a single wizard workflow session."""

    def __init__(self, session_id: str, base_dir: Path):
        self.session_id = session_id
        self.base_dir = base_dir / session_id
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.config: Optional[TopologyConfig] = None
        self.config_path: Optional[str] = None
        self.dataset: Optional[CompliantDataset] = None
        self.raw_df: Optional[pd.DataFrame] = None
        self.benchmark_result: Optional[BenchmarkResult] = None
        self.candidate_models: Dict[str, BaseSurrogateModel] = {}
        self.best_model: Optional[BaseSurrogateModel] = None
        self.selected_model: Optional[BaseSurrogateModel] = None
        self.optimization_result: Optional[OptimizationResult] = None
        self.topsis_result: Optional[Dict[str, Any]] = None
        self.current_step: int = 0
        self.next_step_unlocked: int = 1


class SessionManager:
    """In-memory cache and persistent session workspace manager."""

    def __init__(self, storage_dir: str = "artifacts/sessions"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: Dict[str, SessionState] = {}

    def create_session(self) -> SessionState:
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        session = SessionState(session_id, self.storage_dir)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[SessionState]:
        return self.sessions.get(session_id)


SESSION_MANAGER = SessionManager()

# Global legacy session state for backwards compatibility
SESSION_STATE: Dict[str, Any] = {
    "config": None,
    "config_path": "configs/bridge_amplifier.yaml",
    "dataset": None,
    "benchmark_result": None,
    "optimization_result": None,
    "topsis_result": None,
}


# ==============================================================================
# 3. Wizard Step 1: Topology Discovery & Dataset Validation
# ==============================================================================

@app.get("/api/topologies")
def get_topologies():
    """Return available topology configs with detailed schema, bounds, and symbols."""
    config_dir = Path("configs")
    if not config_dir.exists():
        return {"topologies": []}

    topologies = []
    for f in sorted(config_dir.glob("*.yaml")):
        try:
            cfg = load_topology_config(f)
            topologies.append({
                "filename": f.name,
                "name": cfg.topology.name,
                "description": cfg.topology.description,
                "D_in": cfg.D_in,
                "D_out": cfg.D_out,
                "inputs": [inp.model_dump() for inp in cfg.inputs],
                "outputs": [out.model_dump() for out in cfg.outputs],
                "bounds": {
                    "lower": cfg.bounds[0].tolist(),
                    "upper": cfg.bounds[1].tolist(),
                },
            })
        except Exception:
            continue
    return {"topologies": topologies}


def _resolve_topology_config(topology_name: str) -> TopologyConfig:
    """Find and load topology configuration flexibly by filename or name."""
    cand_paths = [
        Path(topology_name),
        Path("configs") / topology_name,
        Path("configs") / f"{topology_name}.yaml",
    ]
    for p in cand_paths:
        if p.is_file():
            return load_topology_config(p)

    # Search through all yaml configs in configs/
    config_dir = Path("configs")
    if config_dir.is_dir():
        for p in config_dir.glob("*.yaml"):
            try:
                cfg = load_topology_config(p)
                if cfg.topology.name.lower() == topology_name.lower():
                    return cfg
            except Exception:
                continue

    raise HTTPException(
        status_code=400,
        detail=f"Không tìm thấy cấu hình topology: '{topology_name}'. Vui lòng kiểm tra lại thư mục configs/.",
    )


@app.post("/api/wizard/step1-data")
async def wizard_step1_data(
    topology_name: str = Form(...),
    file: Optional[UploadFile] = File(None),
    use_synthetic: bool = Form(False),
    n_synthetic_samples: int = Form(350),
):
    """Step 1: Load topology config and validate/generate dataset."""
    cfg = _resolve_topology_config(topology_name)

    # Validate source options
    if not use_synthetic and (file is None or not file.filename):
        raise HTTPException(
            status_code=400,
            detail="Vui lòng tải lên tệp dữ liệu (CSV/Parquet) hoặc bật tùy chọn sinh dữ liệu tổng hợp (use_synthetic=true).",
        )

    df: pd.DataFrame
    if use_synthetic:
        samples = max(20, min(10000, n_synthetic_samples))
        generator = SyntheticCompliantGenerator(cfg, seed=42)
        df = generator.generate(n_samples=samples, noise_std=0.01)
    else:
        # Read uploaded file
        try:
            content = await file.read()
            if not content:
                raise ValueError("Tệp rỗng không có nội dung.")
            if file.filename.endswith(".parquet"):
                df = pd.read_parquet(io.BytesIO(content))
            else:
                df = pd.read_csv(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Không thể đọc tệp dữ liệu '{file.filename}': {str(e)}",
            )

        # 1. Check missing columns
        missing_inputs = [c for c in cfg.input_names if c not in df.columns]
        missing_outputs = [c for c in cfg.output_names if c not in df.columns]
        missing_cols = missing_inputs + missing_outputs
        if missing_cols:
            raise HTTPException(
                status_code=400,
                detail=f"Tệp dữ liệu thiếu cột: {missing_cols}. Vui lòng kiểm tra lại cấu hình.",
            )

        # 2. Check for Null / NaN
        required_cols = cfg.input_names + cfg.output_names
        if df[required_cols].isna().any().any():
            null_cols = [c for c in required_cols if df[c].isna().any()]
            raise HTTPException(
                status_code=400,
                detail=f"Tệp dữ liệu chứa giá trị rỗng (NaN/Null) tại các cột: {null_cols}. Vui lòng làm sạch dữ liệu trước khi tải lên.",
            )

        # 3. Check numeric data types
        for col in required_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                try:
                    df[col] = pd.to_numeric(df[col])
                except Exception:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cột '{col}' không phải kiểu số. Tất cả các cột đặc trưng phải có kiểu số (numeric).",
                    )

    # Initialize new session
    session = SESSION_MANAGER.create_session()
    session.config = cfg
    session.raw_df = df
    df.to_csv(session.base_dir / "dataset.csv", index=False)

    # Instantiate CompliantDataset
    dataset = CompliantDataset.from_dataframe(df, cfg, random_state=42)
    session.dataset = dataset
    session.current_step = 1
    session.next_step_unlocked = 2

    # Update global legacy state for backward compatibility
    SESSION_STATE["config"] = cfg
    SESSION_STATE["dataset"] = dataset

    preview_rows = df.head(10).to_dict(orient="records")
    return {
        "status": "success",
        "session_id": session.session_id,
        "data_summary": {
            "num_samples": len(df),
            "input_features": cfg.input_names,
            "output_targets": cfg.output_names,
            "preview_rows": preview_rows,
        },
        "next_step_unlocked": 2,
    }


# ==============================================================================
# 4. Wizard Step 2: Multi-Output Model Zoo Training & Benchmark
# ==============================================================================

@app.post("/api/wizard/step2-train")
def wizard_step2_train(req: Step2Request):
    """Step 2: Train Model Zoo, evaluate K-Fold CV, rank models, and extract best surrogate."""
    session = SESSION_MANAGER.get_session(req.session_id)
    if session is None or session.current_step < 1 or session.dataset is None:
        raise HTTPException(
            status_code=400,
            detail="Bước 1 chưa hoàn thành hoặc session không tồn tại. Vui lòng nạp dữ liệu trước.",
        )

    # Re-instantiate dataset with user's selected scaler type
    preprocessor = AdaptivePreprocessor(scaler_type=req.scaler_type)
    dataset = CompliantDataset.from_dataframe(
        session.raw_df, session.config, random_state=42, preprocessor=preprocessor
    )
    session.dataset = dataset

    # Benchmark candidates
    engine = ModelBenchmarkEngine(dataset=dataset, cv_folds=req.cv_folds, seed=42)
    benchmark_res = engine.run_benchmark()
    session.benchmark_result = benchmark_res
    session.best_model = benchmark_res.best_model
    session.candidate_models = getattr(benchmark_res, "fitted_models", {})

    # Persist artifacts in session directory
    session.best_model.save(session.base_dir / "best_surrogate.pkl")
    with open(session.base_dir / "preprocessor.pkl", "wb") as f:
        pickle.dump(dataset.preprocessor, f)
    benchmark_res.to_json(session.base_dir / "leaderboard.json")

    # Also persist to global models/artifacts and reports/
    art_dir = Path("models/artifacts")
    art_dir.mkdir(parents=True, exist_ok=True)
    session.best_model.save(art_dir / "best_surrogate.pkl")
    with open(art_dir / "preprocessor.pkl", "wb") as f:
        pickle.dump(dataset.preprocessor, f)

    rep_dir = Path("reports")
    rep_dir.mkdir(parents=True, exist_ok=True)
    benchmark_res.to_json(rep_dir / "leaderboard.json")

    SESSION_STATE["benchmark_result"] = benchmark_res

    # Build leaderboard summary
    leaderboard = []
    for rec in benchmark_res.records:
        leaderboard.append({
            "model": rec["model_name"],
            "mean_r2": round(float(rec["test_r2_mean"]), 4),
            "cv_r2": round(float(rec["cv_r2_mean"]), 4),
            "rmse": round(float(rec["test_rmse_mean"]), 4),
            "mae": round(float(rec["test_mae_mean"]), 4),
            "latency_ms": round(float(rec["inference_latency_ms"]), 2),
            "is_best": bool(rec["model_name"] == session.best_model.name),
        })

    # Prepare scatter data for best model on test partition
    X_test_scaled, Y_test_scaled = dataset.get_test_data(scaled=True)
    Y_pred_scaled = session.best_model.predict(X_test_scaled)
    Y_pred_raw = dataset.preprocessor.inverse_transform_y(Y_pred_scaled)
    Y_test_raw = dataset.Y_test_raw

    # Primary output index (0)
    target_idx = 0
    scatter_data = {
        "target_name": session.config.output_names[target_idx],
        "actual": [round(float(v), 4) for v in Y_test_raw[:, target_idx]],
        "predicted": [round(float(v), 4) for v in Y_pred_raw[:, target_idx]],
    }

    session.current_step = 2
    session.next_step_unlocked = 3

    return {
        "status": "success",
        "leaderboard": leaderboard,
        "best_model": session.best_model.name,
        "scatter_data": scatter_data,
        "next_step_unlocked": 3,
    }


# ==============================================================================
# 5. Wizard Step 3: Multi-Objective NSGA-II Optimization & TOPSIS
# ==============================================================================

@app.post("/api/wizard/step3-optimize")
def wizard_step3_optimize(req: Step3Request):
    """Step 3: Solve multi-objective problem using NSGA-II and determine knee-point via TOPSIS."""
    session = SESSION_MANAGER.get_session(req.session_id)
    if session is None or session.current_step < 2 or session.best_model is None:
        raise HTTPException(
            status_code=400,
            detail="Bước 2 chưa hoàn thành hoặc chưa có mô hình huấn luyện. Vui lòng chạy benchmark trước.",
        )

    # Determine surrogate model
    surrogate = session.best_model
    if req.selected_model and req.selected_model in session.candidate_models:
        surrogate = session.candidate_models[req.selected_model]
    session.selected_model = surrogate

    # Build Pymoo problem
    problem = CompliantMechanismProblem(
        config=session.config,
        surrogate_model=surrogate,
        preprocessor=session.dataset.preprocessor,
    )

    # Solve via NSGA-II
    solver = NSGA2Solver(
        pop_size=req.pop_size,
        n_generations=req.generations,
        seed=42,
    )
    opt_res = solver.solve(problem)
    session.optimization_result = opt_res

    # MCDM TOPSIS selection
    tradeoff = topsis_select_best_tradeoff(opt_res)
    session.topsis_result = tradeoff

    # Save artifacts to session workspace
    opt_res.to_csv(str(session.base_dir / "pareto_front.csv"))
    with open(session.base_dir / "best_configuration.json", "w", encoding="utf-8") as f:
        json.dump(tradeoff, f, indent=2)

    # Also save to global reports/
    rep_dir = Path("reports")
    rep_dir.mkdir(parents=True, exist_ok=True)
    opt_res.to_csv(str(rep_dir / "pareto_front.csv"))
    with open(rep_dir / "best_configuration.json", "w", encoding="utf-8") as f:
        json.dump(tradeoff, f, indent=2)

    SESSION_STATE["optimization_result"] = opt_res
    SESSION_STATE["topsis_result"] = tradeoff

    # Format pareto points with aliases
    pareto_points = []
    for i in range(opt_res.n_pareto):
        pt = {
            "design": [round(float(v), 4) for v in opt_res.X_pareto[i]],
        }
        for j, out_name in enumerate(session.config.output_names):
            val = round(float(opt_res.Y_pareto[i, j]), 4)
            pt[out_name] = val
            # Standard aliases for charting convenience
            if out_name == "output_displacement":
                pt["F2_displacement"] = val
            elif out_name == "resonant_frequency":
                pt["f_frequency"] = val
            elif out_name == "safety_factor":
                pt["F1_safety"] = val
        pareto_points.append(pt)

    session.current_step = 3
    session.next_step_unlocked = 4

    return {
        "status": "success",
        "pareto_summary": {
            "num_pareto_points": opt_res.n_pareto,
            "execution_time_sec": round(opt_res.runtime_sec, 3),
        },
        "pareto_points": pareto_points,
        "topsis_best_index": tradeoff["best_index"],
        "next_step_unlocked": 4,
    }


# ==============================================================================
# 6. Wizard Step 4: Summary Results & File Exports
# ==============================================================================

@app.get("/api/wizard/step4-results")
def wizard_step4_results(session_id: str = Query(..., description="ID của phiên làm việc")):
    """Step 4: Retrieve final optimal compromise design and accuracy summary."""
    session = SESSION_MANAGER.get_session(session_id)
    if session is None or session.current_step < 3 or session.topsis_result is None:
        raise HTTPException(
            status_code=400,
            detail="Bước 3 chưa hoàn thành hoặc chưa có kết quả tối ưu. Vui lòng chạy NSGA-II trước.",
        )

    model_used = session.selected_model or session.best_model
    return {
        "status": "success",
        "session_id": session_id,
        "topology_name": session.config.topology.name,
        "surrogate_model": model_used.name,
        "recommended_design_inputs": session.topsis_result["recommended_design_inputs"],
        "predicted_mechanical_responses": session.topsis_result["predicted_mechanical_responses"],
        "topsis_score": session.topsis_result["topsis_score"],
        "total_pareto_solutions": session.optimization_result.n_pareto,
        "downloads": {
            "pareto_csv": f"/api/wizard/download/pareto-csv?session_id={session_id}",
            "best_design_json": f"/api/wizard/download/best-design-json?session_id={session_id}",
            "model_pkl": f"/api/wizard/download/model-pkl?session_id={session_id}",
        },
    }


@app.get("/api/wizard/download/pareto-csv")
def wizard_download_pareto_csv(session_id: str = Query(...)):
    """Download pareto_front.csv for the specified session."""
    session = SESSION_MANAGER.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=400, detail="Phiên làm việc không tồn tại.")
    path = session.base_dir / "pareto_front.csv"
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Tệp pareto_front.csv chưa được tạo. Vui lòng hoàn thành Bước 3.",
        )
    return FileResponse(str(path), media_type="text/csv", filename="pareto_front.csv")


@app.get("/api/wizard/download/best-design-json")
def wizard_download_best_design_json(session_id: str = Query(...)):
    """Download best_configuration.json for the specified session."""
    session = SESSION_MANAGER.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=400, detail="Phiên làm việc không tồn tại.")
    path = session.base_dir / "best_configuration.json"
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Tệp best_configuration.json chưa được tạo. Vui lòng hoàn thành Bước 3.",
        )
    return FileResponse(str(path), media_type="application/json", filename="best_configuration.json")


@app.get("/api/wizard/download/model-pkl")
def wizard_download_model_pkl(session_id: str = Query(...)):
    """Download best_surrogate.pkl for the specified session."""
    session = SESSION_MANAGER.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=400, detail="Phiên làm việc không tồn tại.")
    path = session.base_dir / "best_surrogate.pkl"
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Tệp best_surrogate.pkl chưa được tạo. Vui lòng hoàn thành Bước 2.",
        )
    return FileResponse(str(path), media_type="application/octet-stream", filename="best_surrogate.pkl")


# ==============================================================================
# 7. Legacy Endpoints (Maintained for Backward Compatibility)
# ==============================================================================

@app.get("/api/configs")
def list_configs():
    """List available topology configuration YAML files in configs/ directory."""
    config_dir = Path("configs")
    if not config_dir.exists():
        return {"configs": []}
    files = [f.name for f in config_dir.glob("*.yaml")]
    return {"configs": sorted(files)}


@app.get("/api/configs/{filename}")
def get_config_details(filename: str):
    """Retrieve parsed metadata for a specified configuration file."""
    path = Path("configs") / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Configuration file not found.")
    try:
        cfg = load_topology_config(path)
        SESSION_STATE["config"] = cfg
        SESSION_STATE["config_path"] = str(path)
        return {
            "name": cfg.topology.name,
            "description": cfg.topology.description,
            "D_in": cfg.D_in,
            "D_out": cfg.D_out,
            "inputs": [inp.model_dump() for inp in cfg.inputs],
            "outputs": [out.model_dump() for out in cfg.outputs],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/dataset/generate")
def generate_synthetic_dataset(
    config_file: str = Form("bridge_amplifier.yaml"),
    n_samples: int = Form(300),
):
    """Generate synthetic dataset matching selected topology and prepare session dataset."""
    path = Path("configs") / config_file
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Config file not found.")

    cfg = load_topology_config(path)
    SESSION_STATE["config"] = cfg
    SESSION_STATE["config_path"] = str(path)

    generator = SyntheticCompliantGenerator(cfg, seed=42)
    df = generator.generate(n_samples=n_samples, noise_std=0.01)

    dataset = CompliantDataset.from_dataframe(df, cfg, random_state=42)
    SESSION_STATE["dataset"] = dataset

    preview = df.head(10).to_dict(orient="records")
    return {
        "status": "success",
        "n_samples": len(df),
        "columns": list(df.columns),
        "preview": preview,
        "input_cols": cfg.input_names,
        "output_cols": cfg.output_names,
    }


@app.post("/api/dataset/upload")
async def upload_dataset(
    file: UploadFile = File(...),
    config_file: str = Form("bridge_amplifier.yaml"),
):
    """Upload CSV dataset and validate against selected topology schema."""
    path = Path("configs") / config_file
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Config file not found.")

    cfg = load_topology_config(path)
    SESSION_STATE["config"] = cfg

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse CSV: {e}")

    missing_inputs = set(cfg.input_names) - set(df.columns)
    missing_outputs = set(cfg.output_names) - set(df.columns)
    if missing_inputs or missing_outputs:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "Dataset column mismatch",
                "missing_inputs": list(missing_inputs),
                "missing_outputs": list(missing_outputs),
            },
        )

    dataset = CompliantDataset.from_dataframe(df, cfg, random_state=42)
    SESSION_STATE["dataset"] = dataset

    return {
        "status": "success",
        "filename": file.filename,
        "n_samples": len(df),
        "columns": list(df.columns),
        "preview": df.head(10).to_dict(orient="records"),
    }


@app.post("/api/benchmark")
def run_benchmark_endpoint(cv_folds: int = Form(3)):
    """Run model zoo benchmarking on the active session dataset."""
    dataset = SESSION_STATE.get("dataset")
    if dataset is None:
        cfg = SESSION_STATE.get("config") or load_topology_config("configs/bridge_amplifier.yaml")
        dataset = CompliantDataset.from_synthetic(cfg, n_samples=300, seed=42)
        SESSION_STATE["dataset"] = dataset
        SESSION_STATE["config"] = cfg

    engine = ModelBenchmarkEngine(dataset=dataset, cv_folds=cv_folds, seed=42)
    candidate_models = [
        PolynomialRSMSurrogate(degree=2),
        XGBoostSurrogate(n_estimators=60, max_depth=3),
        LightGBMSurrogate(n_estimators=60, max_depth=4),
        RandomForestSurrogate(n_estimators=50, max_depth=6),
        MultiOutputGPR(n_restarts_optimizer=0),
    ]

    result = engine.run_benchmark(models=candidate_models)
    SESSION_STATE["benchmark_result"] = result

    art_dir = Path("models/artifacts")
    art_dir.mkdir(parents=True, exist_ok=True)
    result.best_model.save(art_dir / "best_surrogate.pkl")
    with open(art_dir / "preprocessor.pkl", "wb") as f:
        pickle.dump(dataset.preprocessor, f)

    rep_dir = Path("reports")
    rep_dir.mkdir(parents=True, exist_ok=True)
    result.to_json(rep_dir / "leaderboard.json")
    result.to_markdown(rep_dir / "leaderboard.md")

    return {
        "status": "success",
        "best_model_name": result.best_model.name,
        "leaderboard": result.records,
    }


@app.post("/api/optimize")
def run_optimization_endpoint(
    pop_size: int = Form(60),
    generations: int = Form(40),
):
    """Execute NSGA-II multi-objective evolutionary optimization and MCDM TOPSIS knee-point."""
    cfg = SESSION_STATE.get("config") or load_topology_config("configs/bridge_amplifier.yaml")
    benchmark_res = SESSION_STATE.get("benchmark_result")

    if benchmark_res is not None:
        surrogate = benchmark_res.best_model
        preprocessor = SESSION_STATE["dataset"].preprocessor
    else:
        model_path = Path("models/artifacts/best_surrogate.pkl")
        prep_path = Path("models/artifacts/preprocessor.pkl")
        if not model_path.is_file() or not prep_path.is_file():
            run_benchmark_endpoint(cv_folds=2)
        with open("models/artifacts/best_surrogate.pkl", "rb") as f:
            surrogate = pickle.load(f)
        with open("models/artifacts/preprocessor.pkl", "rb") as f:
            preprocessor = pickle.load(f)

    problem = CompliantMechanismProblem(
        config=cfg,
        surrogate_model=surrogate,
        preprocessor=preprocessor,
    )

    solver = NSGA2Solver(pop_size=pop_size, n_generations=generations, seed=42)
    opt_res = solver.solve(problem)
    SESSION_STATE["optimization_result"] = opt_res

    rep_dir = Path("reports")
    rep_dir.mkdir(parents=True, exist_ok=True)
    pareto_csv_path = rep_dir / "pareto_front.csv"
    opt_res.to_csv(str(pareto_csv_path))

    tradeoff = topsis_select_best_tradeoff(opt_res)
    SESSION_STATE["topsis_result"] = tradeoff

    with open(rep_dir / "best_configuration.json", "w", encoding="utf-8") as f:
        json.dump(tradeoff, f, indent=2)

    pareto_df = opt_res.to_dataframe()
    scatter_points = []
    for _, row in pareto_df.iterrows():
        scatter_points.append({
            "displacement": float(row.get("output_displacement", 0)),
            "frequency": float(row.get("resonant_frequency", 0)),
            "safety_factor": float(row.get("safety_factor", 0)),
        })

    knee_point = {
        "displacement": tradeoff["predicted_mechanical_responses"].get("output_displacement", 0),
        "frequency": tradeoff["predicted_mechanical_responses"].get("resonant_frequency", 0),
        "safety_factor": tradeoff["predicted_mechanical_responses"].get("safety_factor", 0),
    }

    return {
        "status": "success",
        "runtime_sec": opt_res.runtime_sec,
        "n_pareto": opt_res.n_pareto,
        "tradeoff": tradeoff,
        "scatter_points": scatter_points,
        "knee_point": knee_point,
    }


@app.get("/api/download/pareto")
def download_pareto_csv():
    path = Path("reports/pareto_front.csv")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Pareto front file not found. Run optimization first.")
    return FileResponse(str(path), media_type="text/csv", filename="pareto_front.csv")


@app.get("/api/download/best-config")
def download_best_config():
    path = Path("reports/best_configuration.json")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Best configuration file not found. Run optimization first.")
    return FileResponse(str(path), media_type="application/json", filename="best_configuration.json")


@app.get("/api/download/model")
def download_model():
    path = Path("models/artifacts/best_surrogate.pkl")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Model artifact file not found. Run benchmark first.")
    return FileResponse(str(path), media_type="application/octet-stream", filename="best_surrogate.pkl")


# ==============================================================================
# 8. Main Dashboard Root Endpoint
# ==============================================================================

@app.get("/", response_class=HTMLResponse)
def index_page():
    """Serve the single-page responsive AutoCompliant-ML dashboard UI."""
    template_path = Path(__file__).parent / "templates" / "index.html"
    if template_path.is_file():
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>AutoCompliant-ML Stepper Wizard</h1>"
