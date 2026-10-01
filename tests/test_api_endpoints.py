"""
API Integration Tests for FastAPI v1 Endpoints.
Verifies Health Check, Hazards API, Route Directions, Voice Parsing, and Model Training APIs.
"""
import pytest
from fastapi.testclient import TestClient
from backend.src.presentation.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data
    # Verify correlation id and response time headers
    assert "X-Correlation-ID" in response.headers
    assert "X-Response-Time-MS" in response.headers


def test_get_hazards_list():
    response = client.get("/api/v1/hazards")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] > 0
    assert len(data["hazards"]) > 0

    # Filter by speed_camera
    filtered = client.get("/api/v1/hazards?type=speed_camera")
    assert filtered.status_code == 200
    f_data = filtered.json()
    for h in f_data["hazards"]:
        assert h["type"] == "speed_camera"


def test_check_proximity_api():
    # Coordinates near Hang Xanh
    payload = {
        "latitude": 10.8018,
        "longitude": 106.7115,
        "radius_meters": 300,
    }
    response = client.post("/api/v1/hazards/check-proximity", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["has_alert"] is True
    assert len(data["active_alerts"]) > 0


def test_voice_parse_api():
    payload = {
        "text": "Chỉ đường tới Chợ Bến Thành né ngập nước",
        "language": "vi",
    }
    response = client.post("/api/v1/voice/parse", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "NAVIGATE"
    assert "Bến Thành" in data["entities"]["destination"]
    assert data["entities"]["avoid_floods"] is True


def test_training_status_and_trigger_api():
    # Test GET status
    status_res = client.get("/api/v1/training/status")
    assert status_res.status_code == 200
    s_data = status_res.json()
    assert "metrics" in s_data
    assert s_data["metrics"]["accuracy"] > 0.8

    # Test POST trigger
    trigger_payload = {
        "hyperparameters": {
            "architecture": "tfidf_classifier",
            "epochs": 2,
            "learning_rate": 0.001,
            "batch_size": 16,
            "use_peft_lora": False,
        }
    }
    trigger_res = client.post("/api/v1/training/train", json=trigger_payload)
    assert trigger_res.status_code == 200
    t_data = trigger_res.json()
    assert t_data["success"] is True
    assert "run_id" in t_data
