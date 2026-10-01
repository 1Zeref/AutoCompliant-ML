"""
OSRM Client with Heuristic Offline Fallback for Motorbike Navigation.
Queries Open Source Routing Machine or synthesizes smooth road geometries.
"""
import math
from typing import Dict, Any, List, Tuple, Optional
import httpx
from backend.src.core.config import settings
from backend.src.core.logger import logger


class OSRMClient:
    def __init__(self, base_url: str = settings.osrm_server_url):
        self.base_url = base_url.rstrip("/")

    async def get_route(
        self,
        start_lat: float,
        start_lon: float,
        end_lat: float,
        end_lon: float,
        profile: str = "driving",
    ) -> Dict[str, Any]:
        """
        Queries OSRM API: /route/v1/{profile}/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson
        """
        url = f"{self.base_url}/route/v1/{profile}/{start_lon},{start_lat};{end_lon},{end_lat}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "true",
        }

        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                response = await client.get(url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("code") == "Ok" and data.get("routes"):
                        route = data["routes"][0]
                        # OSRM geojson coordinates are [lon, lat], convert to [lat, lon]
                        coords = [
                            (pt[1], pt[0])
                            for pt in route.get("geometry", {}).get("coordinates", [])
                        ]
                        return {
                            "source": "osrm",
                            "distance_meters": route.get("distance", 0.0),
                            "duration_seconds": route.get("duration", 0.0),
                            "waypoints": coords,
                            "steps": self._extract_steps(route.get("legs", [])),
                        }
        except Exception as e:
            logger.warning(f"OSRM external request failed ({str(e)}), activating heuristic fallback route")

        # Fallback Heuristic Route
        return self._generate_fallback_route(start_lat, start_lon, end_lat, end_lon)

    def _extract_steps(self, legs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        steps = []
        for leg in legs:
            for s in leg.get("steps", []):
                instruction = s.get("maneuver", {}).get("type", "continue")
                name = s.get("name", "")
                desc = f"Đi tiếp vào {name}" if name else f"Đi tiếp theo biển chỉ dẫn ({instruction})"
                steps.append(
                    {
                        "instruction": desc,
                        "distance_meters": s.get("distance", 0.0),
                        "duration_seconds": s.get("duration", 0.0),
                    }
                )
        return steps

    def _generate_fallback_route(
        self, start_lat: float, start_lon: float, end_lat: float, end_lon: float
    ) -> Dict[str, Any]:
        """
        Synthesizes a realistic road route with intermediate urban turns when offline.
        """
        # Linear distance approximation
        dlat = end_lat - start_lat
        dlon = end_lon - start_lon
        rough_dist_m = math.sqrt((dlat * 111000) ** 2 + (dlon * 111000) ** 2) * 1.25  # winding factor
        rough_duration_s = (rough_dist_m / 1000.0) / 32.0 * 3600.0  # ~32 km/h avg motorbike speed

        # Interpolate 10 urban road waypoints
        waypoints: List[Tuple[float, float]] = []
        num_points = 10
        for i in range(num_points + 1):
            t = i / float(num_points)
            # Add slight curvature representing urban street grid
            curve = math.sin(t * math.pi) * 0.0015
            lat = start_lat + t * dlat + curve
            lon = start_lon + t * dlon + (curve * 0.5)
            waypoints.append((round(lat, 6), round(lon, 6)))

        return {
            "source": "fallback_heuristic",
            "distance_meters": round(rough_dist_m, 1),
            "duration_seconds": round(rough_duration_s, 1),
            "waypoints": waypoints,
            "steps": [
                {
                    "instruction": "Khởi hành từ vị trí xuất phát, rẽ vào tuyến đường chính",
                    "distance_meters": round(rough_dist_m * 0.3, 1),
                    "duration_seconds": round(rough_duration_s * 0.3, 1),
                },
                {
                    "instruction": "Đi thẳng theo làn đường xe máy, chú ý các biển báo tốc độ",
                    "distance_meters": round(rough_dist_m * 0.5, 1),
                    "duration_seconds": round(rough_duration_s * 0.5, 1),
                },
                {
                    "instruction": "Đến gần điểm đích, giảm tốc độ và táp vào lề đường",
                    "distance_meters": round(rough_dist_m * 0.2, 1),
                    "duration_seconds": round(rough_duration_s * 0.2, 1),
                },
            ],
        }


osrm_client = OSRMClient()
