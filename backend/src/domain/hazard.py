"""
Domain Entities and Schemas for Spatial Hazards and Alerts.
"""
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class HazardType(str, Enum):
    SPEED_CAMERA = "speed_camera"
    FLOOD_POINT = "flood_point"
    SPEED_LIMIT = "speed_limit"
    TRAFFIC_JAM = "traffic_jam"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


class Hazard(BaseModel):
    id: str
    type: HazardType
    title: str
    description: str
    latitude: float
    longitude: float
    radius_meters: float = 300.0
    severity: Severity = Severity.WARNING
    speed_limit: Optional[int] = None
    is_active: bool = True
    city: str = "Ho_Chi_Minh"


class ProximityAlert(BaseModel):
    hazard_id: str
    type: HazardType
    title: str
    distance_meters: float
    severity: Severity
    speed_limit: Optional[int] = None
    speech_announcement: str


class CheckProximityRequest(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_meters: float = Field(default=300.0, ge=50.0, le=2000.0)
    speed_kmh: Optional[float] = Field(default=0.0, ge=0.0)


class CheckProximityResponse(BaseModel):
    has_alert: bool
    active_alerts: List[ProximityAlert] = []
    user_latitude: float
    user_longitude: float
    timestamp: str
