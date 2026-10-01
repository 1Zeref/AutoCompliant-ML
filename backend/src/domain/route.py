"""
Domain Models for Motorbike Routing and Waypoints.
"""
from typing import List, Tuple, Optional
from pydantic import BaseModel, Field
from backend.src.domain.hazard import Hazard


class RouteRequest(BaseModel):
    start_lat: float = Field(..., ge=-90.0, le=90.0)
    start_lon: float = Field(..., ge=-180.0, le=180.0)
    end_lat: float = Field(..., ge=-90.0, le=90.0)
    end_lon: float = Field(..., ge=-180.0, le=180.0)
    avoid_floods: bool = True
    vehicle_type: str = "motorcycle"


class RouteStep(BaseModel):
    instruction: str
    distance_meters: float
    duration_seconds: float


class RouteResult(BaseModel):
    distance_km: float
    duration_minutes: float
    summary: str
    waypoints: List[Tuple[float, float]] = []  # List of [lat, lon]
    steps: List[RouteStep] = []
    hazards_on_route: List[Hazard] = []
    avoided_floods_count: int = 0
