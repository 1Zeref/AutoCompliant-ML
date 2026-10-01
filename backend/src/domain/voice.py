"""
Domain Models for Hands-Free Voice Assistant and Intent Processing.
"""
from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    NAVIGATE = "NAVIGATE"
    CHECK_HAZARDS = "CHECK_HAZARDS"
    CHECK_FLOOD_WEATHER = "CHECK_FLOOD_WEATHER"
    REPORT_INCIDENT = "REPORT_INCIDENT"
    HELP_GUIDE = "HELP_GUIDE"
    UNKNOWN = "UNKNOWN"


class VoiceRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    current_lat: Optional[float] = None
    current_lon: Optional[float] = None
    language: str = "vi"


class VoiceEntities(BaseModel):
    destination: Optional[str] = None
    hazard_type: Optional[str] = None
    avoid_floods: bool = False
    speed_inquiry: bool = False


class VoiceResponse(BaseModel):
    intent: IntentType
    confidence: float
    entities: VoiceEntities
    voice_response: str
    suggested_action: Optional[str] = None
    metadata: Dict[str, Any] = {}
