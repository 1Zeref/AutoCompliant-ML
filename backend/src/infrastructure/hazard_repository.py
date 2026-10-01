"""
Hazard Repository for spatial hazard querying and persistence.
"""
from typing import List, Optional
from backend.src.domain.hazard import Hazard, HazardType
from backend.src.infrastructure.seed_data import DEFAULT_HAZARDS


class HazardRepository:
    def __init__(self, initial_data: Optional[List[Hazard]] = None):
        self._hazards: List[Hazard] = list(initial_data) if initial_data else list(DEFAULT_HAZARDS)

    def get_all(self, hazard_type: Optional[str] = None, city: Optional[str] = None) -> List[Hazard]:
        results = [h for h in self._hazards if h.is_active]
        if hazard_type and hazard_type != "all":
            results = [h for h in results if h.type == hazard_type or h.type.value == hazard_type]
        if city:
            results = [h for h in results if h.city.lower() == city.lower()]
        return results

    def get_by_id(self, hazard_id: str) -> Optional[Hazard]:
        for h in self._hazards:
            if h.id == hazard_id:
                return h
        return None

    def add_hazard(self, hazard: Hazard) -> Hazard:
        self._hazards.append(hazard)
        return hazard


hazard_repo = HazardRepository()
