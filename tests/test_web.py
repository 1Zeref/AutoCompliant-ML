"""Unit tests for FastAPI WebUI and End-to-End Pipeline endpoints (Loop 6 Gate)."""

import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from autocompliant.web.app import app

client = TestClient(app)


def test_web_index_page():
    """Verify that the dashboard HTML root endpoint is accessible."""
    response = client.get("/")
    assert response.status_code == 200
    assert "AutoCompliant-ML" in response.text
    assert "chart.js" in response.text.lower()


def test_api_list_configs():
    """Verify listing of available YAML topology configurations."""
    response = client.get("/api/configs")
    assert response.status_code == 200
    data = response.json()
    assert "configs" in data
    assert "bridge_amplifier.yaml" in data["configs"]
    assert "scott_russell.yaml" in data["configs"]


def test_api_get_config_details():
    """Verify retrieving topology details and metadata."""
    response = client.get("/api/configs/bridge_amplifier.yaml")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bridge_Type_Amplifier"
    assert data["D_in"] == 5
    assert data["D_out"] == 3
    assert len(data["inputs"]) == 5
    assert len(data["outputs"]) == 3


def test_api_dataset_generate():
    """Verify synthetic dataset generation endpoint."""
    response = client.post(
        "/api/dataset/generate",
        data={"config_file": "bridge_amplifier.yaml", "n_samples": 80},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["n_samples"] == 80
    assert len(data["preview"]) > 0
    assert "hinge_thickness_t" in data["columns"]


def test_api_dataset_upload_validation():
    """Verify dataset upload validation with valid and invalid CSV schemas."""
    # 1. Valid CSV
    valid_df = pd.DataFrame({
        "hinge_thickness_t": [0.5, 0.8],
        "hinge_width_w": [10.0, 12.0],
        "arm_length_l": [25.0, 30.0],
        "bridge_angle_theta": [6.0, 8.0],
        "hinge_fillet_r": [1.2, 1.5],
        "safety_factor": [2.1, 2.3],
        "output_displacement": [55.0, 60.0],
        "resonant_frequency": [650.0, 700.0],
    })
    csv_bytes = valid_df.to_csv(index=False).encode("utf-8")

    res_valid = client.post(
        "/api/dataset/upload",
        files={"file": ("test.csv", io.BytesIO(csv_bytes), "text/csv")},
        data={"config_file": "bridge_amplifier.yaml"},
    )
    assert res_valid.status_code == 200
    assert res_valid.json()["n_samples"] == 2

    # 2. Invalid CSV (missing columns)
    invalid_df = pd.DataFrame({"dummy_col": [1, 2]})
    invalid_bytes = invalid_df.to_csv(index=False).encode("utf-8")

    res_invalid = client.post(
        "/api/dataset/upload",
        files={"file": ("invalid.csv", io.BytesIO(invalid_bytes), "text/csv")},
        data={"config_file": "bridge_amplifier.yaml"},
    )
    assert res_invalid.status_code == 422
    assert "column mismatch" in res_invalid.text


def test_api_benchmark_and_optimization_pipeline():
    """Verify end-to-end flow from benchmark through NSGA-II optimization and download."""
    # First ensure a dataset is generated
    client.post(
        "/api/dataset/generate",
        data={"config_file": "bridge_amplifier.yaml", "n_samples": 120},
    )

    # 1. Run Benchmark
    res_bench = client.post("/api/benchmark", data={"cv_folds": 2})
    assert res_bench.status_code == 200
    bench_data = res_bench.json()
    assert bench_data["status"] == "success"
    assert "best_model_name" in bench_data
    assert len(bench_data["leaderboard"]) >= 4

    # 2. Run Optimization
    res_opt = client.post(
        "/api/optimize", data={"pop_size": 30, "generations": 15}
    )
    assert res_opt.status_code == 200
    opt_data = res_opt.json()
    assert opt_data["status"] == "success"
    assert opt_data["n_pareto"] > 0
    assert "tradeoff" in opt_data
    assert "knee_point" in opt_data
    assert len(opt_data["scatter_points"]) == opt_data["n_pareto"]

    # 3. Test File Downloads
    res_dl_pareto = client.get("/api/download/pareto")
    assert res_dl_pareto.status_code == 200
    assert "text/csv" in res_dl_pareto.headers["content-type"]

    res_dl_config = client.get("/api/download/best-config")
    assert res_dl_config.status_code == 200
    assert "application/json" in res_dl_config.headers["content-type"]

    res_dl_model = client.get("/api/download/model")
    assert res_dl_model.status_code == 200
