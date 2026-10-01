"""
Hazard Service with Haversine Geofencing and Natural Voice Announcements.
Provides high-performance spatial proximity checks (< 5ms).
"""
import math
from datetime import datetime, timezone
from typing import List, Tuple
from backend.src.domain.hazard import (
    Hazard,
    HazardType,
    ProximityAlert,
    CheckProximityRequest,
    CheckProximityResponse,
    Severity,
)
from backend.src.infrastructure.hazard_repository import HazardRepository, hazard_repo
from backend.src.core.logger import logger

EARTH_RADIUS_METERS = 6371000.0


def calculate_haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculates great-circle distance between two GPS coordinates in meters
    using the Haversine formula.
    """
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


class HazardService:
    def __init__(self, repository: HazardRepository = hazard_repo):
        self.repository = repository

    def format_speech_announcement(self, hazard: Hazard, distance_m: float) -> str:
        """Generates natural Vietnamese text for speech synthesis."""
        dist_rounded = int(round(distance_m / 10.0) * 10)
        if dist_rounded < 50:
            dist_str = "ngay phía trước"
        else:
            dist_str = f"phía trước khoảng {dist_rounded} mét"

        if hazard.type == HazardType.SPEED_CAMERA:
            speed_txt = f", giới hạn {hazard.speed_limit} km/h" if hazard.speed_limit else ""
            return f"Chú ý: {dist_str} có {hazard.title}{speed_txt}. Vui lòng chú ý quan sát và giữ đúng làn đường."
        elif hazard.type == HazardType.FLOOD_POINT:
            return f"Cảnh báo an toàn: {dist_str} có {hazard.title}. Đoạn đường có nguy cơ ngập nước, hãy cân nhắc giảm tốc độ hoặc chuyển hướng."
        elif hazard.type == HazardType.SPEED_LIMIT:
            speed_val = hazard.speed_limit or 50
            return f"Nhắc nhở tốc độ: {dist_str} bắt đầu {hazard.title}, tốc độ tối đa cho phép là {speed_val} km/h."
        elif hazard.type == HazardType.TRAFFIC_JAM:
            return f"Thông báo giao thông: {dist_str} có {hazard.title}, mật độ xe đông đúc."
        return f"Cảnh báo: {dist_str} có {hazard.title}."

    def check_proximity(self, request: CheckProximityRequest) -> CheckProximityResponse:
        hazards = self.repository.get_all()
        alerts: List[ProximityAlert] = []

        for h in hazards:
            dist = calculate_haversine_distance(
                request.latitude, request.longitude, h.latitude, h.longitude
            )
            threshold = max(h.radius_meters, request.radius_meters)
            if dist <= threshold:
                speech = self.format_speech_announcement(h, dist)
                alerts.append(
                    ProximityAlert(
                        hazard_id=h.id,
                        type=h.type,
                        title=h.title,
                        distance_meters=round(dist, 1),
                        severity=h.severity,
                        speed_limit=h.speed_limit,
                        speech_announcement=speech,
                    )
                )

        # Sort nearest first
        alerts.sort(key=lambda a: a.distance_meters)

        logger.info(
            f"Proximity check at ({request.latitude}, {request.longitude}): found {len(alerts)} alerts"
        )

        return CheckProximityResponse(
            has_alert=len(alerts) > 0,
            active_alerts=alerts,
            user_latitude=request.latitude,
            user_longitude=request.longitude,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def get_all_hazards(self, hazard_type: str = "all", city: str = "") -> List[Hazard]:
        return self.repository.get_all(hazard_type=hazard_type, city=city)


hazard_service = HazardService()
