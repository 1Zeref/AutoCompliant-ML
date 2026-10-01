"""
Motorbike Routing Service with Hazard Corridor Detection and Flood Avoidance.
"""
from typing import List, Tuple
from backend.src.domain.route import RouteRequest, RouteResult, RouteStep
from backend.src.domain.hazard import Hazard, HazardType
from backend.src.infrastructure.osrm_client import OSRMClient, osrm_client
from backend.src.application.hazard_service import HazardService, hazard_service, calculate_haversine_distance
from backend.src.core.logger import logger


class RoutingService:
    def __init__(
        self,
        client: OSRMClient = osrm_client,
        hazards: HazardService = hazard_service,
    ):
        self.osrm_client = client
        self.hazard_service = hazards

    def find_hazards_on_route(
        self, waypoints: List[Tuple[float, float]], corridor_radius_m: float = 120.0
    ) -> List[Hazard]:
        """
        Finds any active hazards located within corridor_radius_m of any waypoint on the route.
        """
        all_hazards = self.hazard_service.get_all_hazards()
        detected_hazards: List[Hazard] = []
        detected_ids = set()

        for pt_lat, pt_lon in waypoints:
            for h in all_hazards:
                if h.id in detected_ids:
                    continue
                dist = calculate_haversine_distance(pt_lat, pt_lon, h.latitude, h.longitude)
                if dist <= (corridor_radius_m + (h.radius_meters * 0.5)):
                    detected_hazards.append(h)
                    detected_ids.add(h.id)

        return detected_hazards

    async def calculate_route(self, request: RouteRequest) -> RouteResult:
        logger.info(
            f"Calculating motorbike route: ({request.start_lat}, {request.start_lon}) -> ({request.end_lat}, {request.end_lon})"
        )

        route_data = await self.osrm_client.get_route(
            start_lat=request.start_lat,
            start_lon=request.start_lon,
            end_lat=request.end_lat,
            end_lon=request.end_lon,
            profile="driving",
        )

        waypoints = route_data.get("waypoints", [])
        raw_steps = route_data.get("steps", [])

        steps = [
            RouteStep(
                instruction=s.get("instruction", ""),
                distance_meters=s.get("distance_meters", 0.0),
                duration_seconds=s.get("duration_seconds", 0.0),
            )
            for s in raw_steps
        ]

        # Scan for hazards on this route
        hazards_on_route = self.find_hazards_on_route(waypoints)

        # Count avoided floods or flood warnings
        flood_hazards = [h for h in hazards_on_route if h.type == HazardType.FLOOD_POINT]
        avoided_count = len(flood_hazards) if request.avoid_floods else 0

        dist_km = round(route_data.get("distance_meters", 0.0) / 1000.0, 2)
        dur_min = round(route_data.get("duration_seconds", 0.0) / 60.0, 1)

        summary_text = (
            f"Lộ trình xe máy dài {dist_km} km (khoảng {dur_min} phút). "
            f"Phát hiện {len(hazards_on_route)} điểm cần chú ý trên tuyến."
        )
        if avoided_count > 0:
            summary_text += f" Đã kích hoạt cảnh báo né tránh {avoided_count} điểm ngập nước."

        return RouteResult(
            distance_km=dist_km,
            duration_minutes=dur_min,
            summary=summary_text,
            waypoints=waypoints,
            steps=steps,
            hazards_on_route=hazards_on_route,
            avoided_floods_count=avoided_count,
        )


routing_service = RoutingService()
