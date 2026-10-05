"""FastAPI Web Application and REST API for AutoCompliant-ML End-to-End Pipeline."""

import io
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse

from autocompliant.config.loader import load_topology_config
from autocompliant.config.schema import TopologyConfig
from autocompliant.data.dataset import CompliantDataset
from autocompliant.data.synthetic_generator import SyntheticCompliantGenerator
from autocompliant.evaluation.benchmark import ModelBenchmarkEngine, BenchmarkResult
from autocompliant.optimization.problem import CompliantMechanismProblem
from autocompliant.optimization.nsga2_solver import NSGA2Solver, OptimizationResult
from autocompliant.optimization.mcdm import topsis_select_best_tradeoff
from autocompliant.models import (
    PolynomialRSMSurrogate,
    RandomForestSurrogate,
    XGBoostSurrogate,
    LightGBMSurrogate,
    MultiOutputGPR,
)

app = FastAPI(
    title="AutoCompliant-ML WebUI",
    description="Config-driven Machine Learning & NSGA-II Optimization Dashboard for Compliant Mechanisms",
    version="1.0.0",
)

# In-memory session state for interactive WebUI workflow
SESSION_STATE: Dict[str, Any] = {
    "config": None,
    "config_path": "configs/bridge_amplifier.yaml",
    "dataset": None,
    "benchmark_result": None,
    "optimization_result": None,
    "topsis_result": None,
}


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

    # Instantiate dataset with preprocessor fitted on train set
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

    # Validate schema
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

    # Persist best model and preprocessor to disk
    art_dir = Path("models/artifacts")
    art_dir.mkdir(parents=True, exist_ok=True)
    result.best_model.save(art_dir / "best_surrogate.pkl")
    with open(art_dir / "preprocessor.pkl", "wb") as f:
        pickle.dump(dataset.preprocessor, f)

    # Save reports
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

    # Load or reuse best model and preprocessor
    if benchmark_res is not None:
        surrogate = benchmark_res.best_model
        preprocessor = SESSION_STATE["dataset"].preprocessor
    else:
        model_path = Path("models/artifacts/best_surrogate.pkl")
        prep_path = Path("models/artifacts/preprocessor.pkl")
        if not model_path.is_file() or not prep_path.is_file():
            # Run quick benchmark first
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

    # Save pareto front CSV
    rep_dir = Path("reports")
    rep_dir.mkdir(parents=True, exist_ok=True)
    pareto_csv_path = rep_dir / "pareto_front.csv"
    opt_res.to_csv(str(pareto_csv_path))

    # Run TOPSIS
    tradeoff = topsis_select_best_tradeoff(opt_res)
    SESSION_STATE["topsis_result"] = tradeoff

    with open(rep_dir / "best_configuration.json", "w", encoding="utf-8") as f:
        json.dump(tradeoff, f, indent=2)

    # Format Pareto front for plotting (F2 vs f)
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


@app.get("/", response_class=HTMLResponse)
def index_page():
    """Serve the single-page responsive AutoCompliant-ML dashboard UI."""
    return HTML_DASHBOARD_TEMPLATE


# Embedded Single Page Application HTML/CSS/JS Template
HTML_DASHBOARD_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AutoCompliant-ML | Compliant Mechanism Pipeline</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --primary: #38bdf8;
      --primary-hover: #0284c7;
      --accent: #f59e0b;
      --success: #10b981;
      --text: #f8fafc;
      --text-muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    body { background-color: var(--bg); color: var(--text); display: flex; flex-direction: column; min-height: 100vh; }
    header { background: #0f172a; border-bottom: 1px solid var(--card-border); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; }
    .logo { font-size: 1.25rem; font-weight: 700; color: var(--primary); display: flex; align-items: center; gap: 0.5rem; }
    .badge { background: #0369a1; color: #e0f2fe; padding: 0.2rem 0.6rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; }
    .container { display: grid; grid-template-columns: 360px 1fr; gap: 1.5rem; padding: 1.5rem; flex: 1; }
    .panel { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 0.75rem; padding: 1.25rem; display: flex; flex-direction: column; gap: 1.25rem; }
    .panel-title { font-size: 1rem; font-weight: 600; border-bottom: 1px solid var(--card-border); padding-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center; }
    .form-group { display: flex; flex-direction: column; gap: 0.35rem; }
    label { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }
    select, input, button { background: #0f172a; border: 1px solid var(--card-border); color: var(--text); padding: 0.6rem 0.8rem; border-radius: 0.375rem; font-size: 0.9rem; }
    select:focus, input:focus { outline: none; border-color: var(--primary); }
    .btn { background: var(--primary); color: #0f172a; font-weight: 600; border: none; cursor: pointer; transition: all 0.2s; text-align: center; }
    .btn:hover { background: var(--primary-hover); }
    .btn-secondary { background: transparent; border: 1px solid var(--card-border); color: var(--text); }
    .btn-secondary:hover { background: #334155; }
    .btn-success { background: var(--success); color: #0f172a; }
    .btn-success:hover { background: #059669; }
    .tabs { display: flex; gap: 0.5rem; border-bottom: 1px solid var(--card-border); padding-bottom: 0.5rem; }
    .tab-btn { background: transparent; border: none; color: var(--text-muted); padding: 0.5rem 1rem; border-radius: 0.375rem; cursor: pointer; font-weight: 600; font-size: 0.9rem; }
    .tab-btn.active { background: #334155; color: var(--primary); }
    .tab-content { display: none; }
    .tab-content.active { display: flex; flex-direction: column; gap: 1.25rem; }
    .table-container { overflow-x: auto; max-height: 280px; }
    table { width: 100%; border-collapse: collapse; font-size: 0.85rem; text-align: left; }
    th { background: #0f172a; padding: 0.6rem; color: var(--text-muted); border-bottom: 1px solid var(--card-border); position: sticky; top: 0; }
    td { padding: 0.55rem; border-bottom: 1px solid var(--card-border); }
    tr:hover { background: #33415522; }
    .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem; }
    .metric-card { background: #0f172a; border: 1px solid var(--card-border); padding: 1rem; border-radius: 0.5rem; text-align: center; }
    .metric-value { font-size: 1.5rem; font-weight: 700; color: var(--primary); margin-top: 0.25rem; }
    .status-log { background: #000; border: 1px solid #1e293b; padding: 0.75rem; border-radius: 0.375rem; font-family: monospace; font-size: 0.8rem; color: #10b981; max-height: 80px; overflow-y: auto; }
    .chart-box { position: relative; height: 350px; background: #0f172a; border-radius: 0.5rem; padding: 1rem; border: 1px solid var(--card-border); }
    .download-bar { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 0.5rem; }
  </style>
</head>
<body>
  <header>
    <div class="logo">
      <span>⚙️ AutoCompliant-ML</span>
      <span class="badge">Pipeline v1.0</span>
    </div>
    <div style="font-size: 0.85rem; color: var(--text-muted);">
      Compliant Mechanism Config-Driven AI & NSGA-II Studio
    </div>
  </header>

  <div class="container">
    <!-- Sidebar Controls -->
    <div class="panel">
      <div class="panel-title">
        <span>1. Topology & Data</span>
      </div>

      <div class="form-group">
        <label>Topology Config</label>
        <select id="configSelect"></select>
      </div>

      <div class="form-group">
        <label>Generate Synthetic FEA Data</label>
        <div style="display: flex; gap: 0.5rem;">
          <input type="number" id="sampleCount" value="300" min="50" max="2000" style="width: 100px;">
          <button class="btn" style="flex:1;" onclick="generateData()">Generate</button>
        </div>
      </div>

      <div class="form-group">
        <label>Or Upload FEA CSV</label>
        <input type="file" id="fileUpload" accept=".csv" onchange="uploadData()">
      </div>

      <div class="panel-title" style="margin-top: 0.5rem;">
        <span>2. Processing Engine</span>
      </div>

      <button class="btn btn-secondary" onclick="runBenchmark()">🚀 Run Model Zoo Benchmark</button>

      <div class="form-group">
        <label>NSGA-II Pop / Gen</label>
        <div style="display: flex; gap: 0.5rem;">
          <input type="number" id="popSize" value="80" style="width: 50%;">
          <input type="number" id="genCount" value="50" style="width: 50%;">
        </div>
      </div>

      <button class="btn btn-success" onclick="runOptimization()">🎯 Run NSGA-II & TOPSIS</button>

      <div class="form-group">
        <label>System Live Log</label>
        <div class="status-log" id="statusLog">> System ready. Select topology or generate data.</div>
      </div>
    </div>

    <!-- Main Display -->
    <div class="panel">
      <div class="tabs">
        <button class="tab-btn active" onclick="switchTab('tab-data')">📊 Dataset Preview</button>
        <button class="tab-btn" onclick="switchTab('tab-bench')">🏆 Model Leaderboard</button>
        <button class="tab-btn" onclick="switchTab('tab-pareto')">📈 Pareto Front & Decision</button>
      </div>

      <!-- Tab 1: Dataset Preview -->
      <div id="tab-data" class="tab-content active">
        <div class="card-grid" id="dataStats">
          <div class="metric-card"><label>Topology</label><div class="metric-value" id="statTopology">-</div></div>
          <div class="metric-card"><label>Samples</label><div class="metric-value" id="statSamples">0</div></div>
          <div class="metric-card"><label>Inputs (Din)</label><div class="metric-value" id="statDin">0</div></div>
          <div class="metric-card"><label>Responses (Dout)</label><div class="metric-value" id="statDout">0</div></div>
        </div>
        <div class="table-container">
          <table id="previewTable">
            <thead><tr id="previewHead"><th>No dataset loaded</th></tr></thead>
            <tbody id="previewBody"></tbody>
          </table>
        </div>
      </div>

      <!-- Tab 2: Benchmark Leaderboard -->
      <div id="tab-bench" class="tab-content">
        <div class="metric-card" style="text-align: left; padding: 0.75rem 1rem;">
          <label>Optimal Surrogate Model Selected:</label>
          <span id="bestModelBadge" style="font-size: 1.1rem; font-weight: 700; color: var(--primary); margin-left: 0.5rem;">None</span>
        </div>
        <div class="table-container">
          <table id="benchTable">
            <thead>
              <tr>
                <th>Rank</th>
                <th>Model</th>
                <th>Test R²</th>
                <th>CV R²</th>
                <th>RMSE</th>
                <th>MAE</th>
                <th>Latency (ms/1k)</th>
              </tr>
            </thead>
            <tbody id="benchBody"><tr><td colspan="7" style="text-align:center;color:var(--text-muted);">Run benchmark to view leaderboard</td></tr></tbody>
          </table>
        </div>
        <div class="download-bar">
          <a class="btn btn-secondary" href="/api/download/model" target="_blank">⬇️ Download best_surrogate.pkl</a>
        </div>
      </div>

      <!-- Tab 3: Pareto Frontier & MCDM -->
      <div id="tab-pareto" class="tab-content">
        <div class="chart-box">
          <canvas id="paretoChart"></canvas>
        </div>
        <div class="panel-title"><span>🏆 TOPSIS Optimal Compromise Design (Knee-Point)</span></div>
        <div class="card-grid" id="tradeoffCards"></div>
        <div class="download-bar">
          <a class="btn btn-secondary" href="/api/download/pareto" target="_blank">⬇️ Download pareto_front.csv</a>
          <a class="btn btn-secondary" href="/api/download/best-config" target="_blank">⬇️ Download best_configuration.json</a>
        </div>
      </div>
    </div>
  </div>

  <script>
    let myChart = null;

    function log(msg) {
      const box = document.getElementById('statusLog');
      box.innerHTML += '<br>> ' + msg;
      box.scrollTop = box.scrollHeight;
    }

    function switchTab(tabId) {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      event.target.classList.add('active');
      document.getElementById(tabId).classList.add('active');
    }

    async function initConfigs() {
      try {
        const res = await fetch('/api/configs');
        const data = await res.json();
        const sel = document.getElementById('configSelect');
        sel.innerHTML = '';
        data.configs.forEach(c => {
          const opt = document.createElement('option');
          opt.value = c;
          opt.innerText = c;
          sel.appendChild(opt);
        });
        if (data.configs.length > 0) loadConfigDetails(data.configs[0]);
      } catch (e) { log('Error fetching configs: ' + e); }
    }

    async function loadConfigDetails(filename) {
      const res = await fetch('/api/configs/' + filename);
      const data = await res.json();
      document.getElementById('statTopology').innerText = data.name;
      document.getElementById('statDin').innerText = data.D_in;
      document.getElementById('statDout').innerText = data.D_out;
      log('Loaded config ' + filename + ' (Din=' + data.D_in + ', Dout=' + data.D_out + ')');
    }

    document.getElementById('configSelect').addEventListener('change', (e) => loadConfigDetails(e.target.value));

    async function generateData() {
      const cfg = document.getElementById('configSelect').value;
      const count = document.getElementById('sampleCount').value;
      log('Generating ' + count + ' synthetic samples...');
      const form = new FormData();
      form.append('config_file', cfg);
      form.append('n_samples', count);

      const res = await fetch('/api/dataset/generate', { method: 'POST', body: form });
      const data = await res.json();
      renderTable(data);
      log('Generated ' + data.n_samples + ' samples successfully.');
    }

    async function uploadData() {
      const input = document.getElementById('fileUpload');
      if (!input.files[0]) return;
      const cfg = document.getElementById('configSelect').value;
      log('Uploading ' + input.files[0].name + '...');
      const form = new FormData();
      form.append('file', input.files[0]);
      form.append('config_file', cfg);

      const res = await fetch('/api/dataset/upload', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) {
        log('Upload error: ' + JSON.stringify(data.detail));
        return;
      }
      renderTable(data);
      log('Uploaded and validated ' + data.n_samples + ' samples.');
    }

    function renderTable(data) {
      document.getElementById('statSamples').innerText = data.n_samples;
      const head = document.getElementById('previewHead');
      head.innerHTML = data.columns.map(c => '<th>' + c + '</th>').join('');
      const body = document.getElementById('previewBody');
      body.innerHTML = data.preview.map(row => {
        return '<tr>' + data.columns.map(c => '<td>' + (typeof row[c] === 'number' ? row[c].toFixed(3) : row[c]) + '</td>').join('') + '</tr>';
      }).join('');
    }

    async function runBenchmark() {
      log('Running Model Zoo comparative benchmark...');
      const form = new FormData();
      form.append('cv_folds', 3);
      const res = await fetch('/api/benchmark', { method: 'POST', body: form });
      const data = await res.json();

      document.getElementById('bestModelBadge').innerText = data.best_model_name;
      const body = document.getElementById('benchBody');
      body.innerHTML = data.leaderboard.map(rec => {
        return '<tr>' +
          '<td><b>#' + rec.rank + '</b></td>' +
          '<td>' + rec.model_name + '</td>' +
          '<td>' + rec.test_r2_mean.toFixed(4) + '</td>' +
          '<td>' + rec.cv_r2_mean.toFixed(4) + '</td>' +
          '<td>' + rec.test_rmse_mean.toFixed(4) + '</td>' +
          '<td>' + rec.test_mae_mean.toFixed(4) + '</td>' +
          '<td>' + rec.inference_latency_ms.toFixed(2) + ' ms</td>' +
        '</tr>';
      }).join('');
      log('Benchmark finished! Best Model: ' + data.best_model_name);
      document.querySelectorAll('.tab-btn')[1].click();
    }

    async function runOptimization() {
      const pop = document.getElementById('popSize').value;
      const gen = document.getElementById('genCount').value;
      log('Executing NSGA-II (Pop: ' + pop + ', Gen: ' + gen + ')...');
      const form = new FormData();
      form.append('pop_size', pop);
      form.append('generations', gen);

      const res = await fetch('/api/optimize', { method: 'POST', body: form });
      const data = await res.json();

      log('Optimization completed in ' + data.runtime_sec.toFixed(3) + 's! Discovered ' + data.n_pareto + ' Pareto solutions.');
      renderParetoChart(data.scatter_points, data.knee_point);
      renderTradeoff(data.tradeoff);
      document.querySelectorAll('.tab-btn')[2].click();
    }

    function renderParetoChart(points, knee) {
      const ctx = document.getElementById('paretoChart').getContext('2d');
      if (myChart) myChart.destroy();

      const scatterData = points.map(p => ({ x: p.displacement, y: p.frequency }));
      const kneeData = [{ x: knee.displacement, y: knee.frequency }];

      myChart = new Chart(ctx, {
        type: 'scatter',
        data: {
          datasets: [
            {
              label: 'Non-dominated Pareto Front',
              data: scatterData,
              backgroundColor: '#38bdf8',
              borderColor: '#0284c7',
              pointRadius: 4,
            },
            {
              label: '⭐ TOPSIS Knee-Point',
              data: kneeData,
              backgroundColor: '#f59e0b',
              borderColor: '#ffffff',
              borderWidth: 2,
              pointRadius: 9,
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              title: { display: true, text: 'Max Output Displacement Δout (µm)', color: '#94a3b8' },
              grid: { color: '#33415544' },
              ticks: { color: '#f8fafc' }
            },
            y: {
              title: { display: true, text: 'Resonant Frequency f1 (Hz)', color: '#94a3b8' },
              grid: { color: '#33415544' },
              ticks: { color: '#f8fafc' }
            }
          },
          plugins: {
            legend: { labels: { color: '#f8fafc' } }
          }
        }
      });
    }

    function renderTradeoff(tradeoff) {
      const box = document.getElementById('tradeoffCards');
      let html = '';
      for (const [k, v] of Object.entries(tradeoff.recommended_design_inputs)) {
        html += '<div class="metric-card"><label>' + k + '</label><div class="metric-value" style="font-size:1.15rem;">' + v.toFixed(3) + '</div></div>';
      }
      for (const [k, v] of Object.entries(tradeoff.predicted_mechanical_responses)) {
        html += '<div class="metric-card" style="border-color:#38bdf8;"><label style="color:#38bdf8;">' + k + '</label><div class="metric-value" style="color:#10b981;font-size:1.15rem;">' + v.toFixed(3) + '</div></div>';
      }
      box.innerHTML = html;
    }

    window.onload = () => {
      initConfigs();
      generateData();
    };
  </script>
</body>
</html>
"""
