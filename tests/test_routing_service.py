"""
TDD Unit Tests for Motorbike Routing Service and Hazard Corridor Detection.
"""
import asyncio
import pytest
from backend.src.domain.route import RouteRequest
from backend.src.domain.hazard import Hazard, HazardType, Severity
from backend.src.application.routing_service import RoutingService
from backend.src.infrastructure.osrm_client import OSRMClient
from backend.src.application.hazard_service import HazardService
from backend.src.infrastructure.hazard_repository import HazardRepository


def test_routing_calculation_fallback():
    client = OSRMClient(base_url="https://invalid-osrm-offline-url.local")
    service = RoutingService(client=client)

    req = RouteRequest(
        start_lat=10.8018,
        start_lon=106.7115,
        end_lat=10.7725,
        end_lon=106.6980,
        avoid_floods=True,
    )
    result = asyncio.run(service.calculate_route(req))

    assert result.distance_km > 0.0
    assert result.duration_minutes > 0.0
    assert len(result.waypoints) > 5
    assert len(result.steps) > 0


def test_routing_corridor_detects_hazards():
    # Place a flood hazard right near the start point
    flood_hazard = Hazard(
        id="flood-corridor-01",
        type=HazardType.FLOOD_POINT,
        title="Test Flood Spot",
        description="Ngập sâu",
        latitude=10.8018,
        longitude=106.7115,
        radius_meters=300.0,
        severity=Severity.WARNING,
        is_active=True,
    )
    repo = HazardRepository(initial_data=[flood_hazard])
    hazard_svc = HazardService(repository=repo)

    client = OSRMClient(base_url="https://invalid-offline.local")
    routing_svc = RoutingService(client=client, hazards=hazard_svc)

    req = RouteRequest(
        start_lat=10.8018,
        start_lon=106.7115,
        end_lat=10.7725,
        end_lon=106.6980,
        avoid_floods=True,
    )
    result = asyncio.run(routing_svc.calculate_route(req))

    assert len(result.hazards_on_route) >= 1
    assert result.hazards_on_route[0].id == "flood-corridor-01"
    assert result.avoided_floods_count >= 1
