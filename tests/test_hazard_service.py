"""
TDD Unit Tests for Spatial Hazard Service and Haversine Distance.
"""
import pytest
from backend.src.domain.hazard import (
    Hazard,
    HazardType,
    CheckProximityRequest,
    Severity,
)
from backend.src.application.hazard_service import (
    calculate_haversine_distance,
    HazardService,
)
from backend.src.infrastructure.hazard_repository import HazardRepository


def test_calculate_haversine_distance_zero():
    # Distance from point to itself is 0
    dist = calculate_haversine_distance(10.8018, 106.7115, 10.8018, 106.7115)
    assert dist == 0.0


def test_calculate_haversine_distance_accurate():
    # Distance between Hang Xanh (10.8018, 106.7115) and Saigon Bridge (10.7997, 106.7214) is approx 1100m - 1200m
    dist = calculate_haversine_distance(10.8018, 106.7115, 10.7997, 106.7214)
    assert 1000.0 < dist < 1300.0


def test_hazard_proximity_trigger_in_radius():
    mock_hazard = Hazard(
        id="test-cam-01",
        type=HazardType.SPEED_CAMERA,
        title="Test Camera Hang Xanh",
        description="Speed limit 50",
        latitude=10.8018,
        longitude=106.7115,
        radius_meters=300.0,
        severity=Severity.DANGER,
        speed_limit=50,
        is_active=True,
    )
    repo = HazardRepository(initial_data=[mock_hazard])
    service = HazardService(repository=repo)

    # Rider is 100m away
    req = CheckProximityRequest(
        latitude=10.8025,
        longitude=106.7115,
        radius_meters=300.0,
    )
    res = service.check_proximity(req)

    assert res.has_alert is True
    assert len(res.active_alerts) == 1
    assert res.active_alerts[0].hazard_id == "test-cam-01"
    assert "Chú ý" in res.active_alerts[0].speech_announcement
    assert "50 km/h" in res.active_alerts[0].speech_announcement


def test_hazard_proximity_outside_radius():
    mock_hazard = Hazard(
        id="test-cam-01",
        type=HazardType.SPEED_CAMERA,
        title="Test Camera",
        description="Speed limit 50",
        latitude=10.8018,
        longitude=106.7115,
        radius_meters=200.0,
        is_active=True,
    )
    repo = HazardRepository(initial_data=[mock_hazard])
    service = HazardService(repository=repo)

    # Rider is 10km away (District 7)
    req = CheckProximityRequest(
        latitude=10.7300,
        longitude=106.7100,
        radius_meters=200.0,
    )
    res = service.check_proximity(req)

    assert res.has_alert is False
    assert len(res.active_alerts) == 0
