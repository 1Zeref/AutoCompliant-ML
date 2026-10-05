"""Unit tests for FastAPI WebUI and Guided Stepper Wizard End-to-End Pipeline."""

import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from autocompliant.web.app import app

client = TestClient(app)


def test_web_index_page():
    """Verify that the dashboard HTML root endpoint is accessible and loads wizard."""
    response = client.get("/")
    assert response.status_code == 200
    assert "AutoCompliant-ML" in response.text
    assert "plotly" in response.text.lower()
    assert "chart.js" in response.text.lower()


def test_get_topologies():
    """Verify listing available topologies with detailed schema and bounds."""
    response = client.get("/api/topologies")
    assert response.status_code == 200
    data = response.json()
    assert "topologies" in data
    topos = {t["filename"]: t for t in data["topologies"]}
    assert "bridge_amplifier.yaml" in topos
    assert topos["bridge_amplifier.yaml"]["D_in"] == 5
    assert topos["bridge_amplifier.yaml"]["D_out"] == 3
    assert "bounds" in topos["bridge_amplifier.yaml"]


def test_step1_validation_failure():
    """Verify that invalid CSV (missing required columns) is blocked with HTTP 400 and clear message."""
    invalid_df = pd.DataFrame({"dummy_feature": [1.0, 2.0], "dummy_target": [3.0, 4.0]})
    csv_bytes = invalid_df.to_csv(index=False).encode("utf-8")

    response = client.post(
        "/api/wizard/step1-data",
        data={"topology_name": "bridge_amplifier.yaml", "use_synthetic": "false"},
        files={"file": ("invalid.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 400
    assert "thiếu cột" in response.json()["detail"].lower()


def test_step1_success():
    """Verify valid synthetic dataset generation creates session and unlocks Step 2."""
    response = client.post(
        "/api/wizard/step1-data",
        data={
            "topology_name": "bridge_amplifier.yaml",
            "use_synthetic": "true",
            "n_synthetic_samples": 80,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "session_id" in data
    assert data["session_id"].startswith("sess_")
    assert data["next_step_unlocked"] == 2
    assert data["data_summary"]["num_samples"] == 80
    assert len(data["data_summary"]["preview_rows"]) > 0


def test_step2_unauthorized_skip():
    """Verify server-side gate blocks Step 2 request if Step 1 is incomplete or session is invalid."""
    response = client.post(
        "/api/wizard/step2-train",
        json={"session_id": "sess_non_existent", "cv_folds": 2, "scaler_type": "standard"},
    )
    assert response.status_code == 400
    assert "chưa hoàn thành" in response.json()["detail"].lower()


def test_step3_unauthorized_skip():
    """Verify server-side gate blocks Step 3 request if Step 2 is not completed."""
    response = client.post(
        "/api/wizard/step3-optimize",
        json={"session_id": "sess_fake123", "pop_size": 40, "generations": 20},
    )
    assert response.status_code == 400
    assert "chưa hoàn thành" in response.json()["detail"].lower()


def test_step4_unauthorized_skip():
    """Verify server-side gate blocks Step 4 request if Step 3 is not completed."""
    response = client.get("/api/wizard/step4-results", params={"session_id": "sess_fake123"})
    assert response.status_code == 400
    assert "chưa hoàn thành" in response.json()["detail"].lower()


def test_full_wizard_pipeline():
    """Verify continuous execution from Step 1 -> Step 2 -> Step 3 -> Step 4 -> file downloads."""
    # Step 1: Initialize Data
    res_s1 = client.post(
        "/api/wizard/step1-data",
        data={
            "topology_name": "bridge_amplifier.yaml",
            "use_synthetic": "true",
            "n_synthetic_samples": 120,
        },
    )
    assert res_s1.status_code == 200
    s1_data = res_s1.json()
    session_id = s1_data["session_id"]
    assert s1_data["next_step_unlocked"] == 2

    # Step 2: Train & Benchmark
    res_s2 = client.post(
        "/api/wizard/step2-train",
        json={"session_id": session_id, "cv_folds": 2, "scaler_type": "standard"},
    )
    assert res_s2.status_code == 200
    s2_data = res_s2.json()
    assert s2_data["status"] == "success"
    assert "best_model" in s2_data
    assert len(s2_data["leaderboard"]) >= 5
    assert "actual" in s2_data["scatter_data"]
    assert "predicted" in s2_data["scatter_data"]
    assert s2_data["next_step_unlocked"] == 3

    # Step 3: Optimize via NSGA-II & TOPSIS
    res_s3 = client.post(
        "/api/wizard/step3-optimize",
        json={"session_id": session_id, "pop_size": 30, "generations": 15},
    )
    assert res_s3.status_code == 200
    s3_data = res_s3.json()
    assert s3_data["status"] == "success"
    assert s3_data["pareto_summary"]["num_pareto_points"] > 0
    assert len(s3_data["pareto_points"]) > 0
    assert s3_data["next_step_unlocked"] == 4

    # Step 4: Results & Summary
    res_s4 = client.get("/api/wizard/step4-results", params={"session_id": session_id})
    assert res_s4.status_code == 200
    s4_data = res_s4.json()
    assert s4_data["status"] == "success"
    assert "recommended_design_inputs" in s4_data
    assert "predicted_mechanical_responses" in s4_data
    assert "topsis_score" in s4_data

    # File Downloads
    res_dl_pareto = client.get(
        "/api/wizard/download/pareto-csv", params={"session_id": session_id}
    )
    assert res_dl_pareto.status_code == 200
    assert "text/csv" in res_dl_pareto.headers["content-type"]
    assert "output_displacement" in res_dl_pareto.text

    res_dl_config = client.get(
        "/api/wizard/download/best-design-json", params={"session_id": session_id}
    )
    assert res_dl_config.status_code == 200
    assert "application/json" in res_dl_config.headers["content-type"]

    res_dl_model = client.get(
        "/api/wizard/download/model-pkl", params={"session_id": session_id}
    )
    assert res_dl_model.status_code == 200


# Legacy endpoint tests
def test_api_list_configs():
    """Verify legacy configs listing."""
    response = client.get("/api/configs")
    assert response.status_code == 200
    data = response.json()
    assert "configs" in data
    assert "bridge_amplifier.yaml" in data["configs"]


def test_api_get_config_details():
    """Verify legacy config details."""
    response = client.get("/api/configs/bridge_amplifier.yaml")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Bridge_Type_Amplifier"


def test_api_dataset_generate():
    """Verify legacy synthetic dataset generation endpoint."""
    response = client.post(
        "/api/dataset/generate",
        data={"config_file": "bridge_amplifier.yaml", "n_samples": 80},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_api_dataset_upload_validation():
    """Verify legacy dataset upload validation."""
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


def test_api_benchmark_and_optimization_pipeline():
    """Verify legacy benchmark and optimization endpoints."""
    client.post(
        "/api/dataset/generate",
        data={"config_file": "bridge_amplifier.yaml", "n_samples": 100},
    )
    res_bench = client.post("/api/benchmark", data={"cv_folds": 2})
    assert res_bench.status_code == 200
    res_opt = client.post("/api/optimize", data={"pop_size": 30, "generations": 15})
    assert res_opt.status_code == 200
