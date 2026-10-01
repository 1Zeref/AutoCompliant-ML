"""
API v1 Router with strict OpenAPI 3.0 contracts and input validations.
"""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from backend.src.core.config import settings
from backend.src.domain.hazard import (
    Hazard,
    CheckProximityRequest,
    CheckProximityResponse,
)
from backend.src.domain.route import RouteRequest, RouteResult
from backend.src.domain.voice import VoiceRequest, VoiceResponse
from backend.src.domain.training import TrainingStatus, TrainingTriggerRequest
from backend.src.application.hazard_service import hazard_service
from backend.src.application.routing_service import routing_service
from backend.src.application.voice_intent_service import voice_intent_service
from backend.src.application.training_service import training_service

router = APIRouter(prefix="/api/v1")


@router.get("/health", summary="Health check endpoint for Docker and monitoring")
async def health_check():
    return {
        "status": "ok",
        "app_name": settings.app_name,
        "env": settings.app_env,
        "version": settings.version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# --- HAZARDS ---
@router.get("/hazards", summary="Get list of traffic hazards")
async def get_hazards(
    type: Optional[str] = Query(default="all", description="Filter by type: speed_camera, flood_point, speed_limit, traffic_jam"),
    city: Optional[str] = Query(default="", description="Filter by city: Ho_Chi_Minh, Ha_Noi"),
):
    items = hazard_service.get_all_hazards(hazard_type=type, city=city)
    return {
        "total": len(items),
        "hazards": items,
    }


@router.post("/hazards/check-proximity", response_model=CheckProximityResponse, summary="Check spatial proximity to hazards")
async def check_hazard_proximity(request: CheckProximityRequest):
    return hazard_service.check_proximity(request)


# --- ROUTING ---
@router.post("/routes/directions", response_model=RouteResult, summary="Calculate motorbike route")
async def get_route_directions(request: RouteRequest):
    return await routing_service.calculate_route(request)


# --- VOICE NLP ---
@router.post("/voice/parse", response_model=VoiceResponse, summary="Parse speech utterance into intent and entities")
async def parse_voice(request: VoiceRequest):
    return voice_intent_service.parse(request)


# --- TRAINING ---
@router.get("/training/status", response_model=TrainingStatus, summary="Get training status and model metrics")
async def get_training_status():
    return training_service.get_status()


@router.post("/training/train", summary="Trigger background training job")
async def trigger_model_training(request: TrainingTriggerRequest):
    return await training_service.trigger_training(request)
