"""
TDD Unit Tests for Vietnamese Voice Intent NLP Parser.
"""
import pytest
from backend.src.domain.voice import VoiceRequest, IntentType
from backend.src.application.voice_intent_service import (
    normalize_vietnamese_text,
    VoiceIntentService,
)


def test_normalize_vietnamese_text():
    raw = "  Chỉ đường tới Chợ Bến Thành, tránh ngập nước???  "
    norm = normalize_vietnamese_text(raw)
    assert norm == "chỉ đường tới chợ bến thành tránh ngập nước"


def test_voice_intent_navigate():
    service = VoiceIntentService()
    req = VoiceRequest(text="Chỉ đường tới Chợ Bến Thành né ngập nước nha")
    res = service.parse(req)

    assert res.intent == IntentType.NAVIGATE
    assert res.confidence >= 0.90
    assert "Bến Thành" in res.entities.destination
    assert res.entities.avoid_floods is True
    assert "Bến Thành" in res.voice_response
    assert res.suggested_action == "START_NAVIGATION"


def test_voice_intent_check_camera():
    service = VoiceIntentService()
    req = VoiceRequest(text="Phía trước có camera phạt nguội hay bắn tốc độ không?")
    res = service.parse(req)

    assert res.intent == IntentType.CHECK_HAZARDS
    assert res.confidence >= 0.90
    assert "camera" in res.voice_response.lower()
    assert res.suggested_action == "SCAN_HAZARDS"


def test_voice_intent_check_flood():
    service = VoiceIntentService()
    req = VoiceRequest(text="Đoạn đường Nguyễn Hữu Cảnh này có ngập nước không?")
    res = service.parse(req)

    assert res.intent == IntentType.CHECK_FLOOD_WEATHER
    assert res.confidence >= 0.90
    assert "ngập" in res.voice_response.lower()
    assert res.suggested_action == "SCAN_FLOODS"


def test_voice_intent_report_incident():
    service = VoiceIntentService()
    req = VoiceRequest(text="Báo cáo kẹt xe nghiêm trọng tại giao lộ này")
    res = service.parse(req)

    assert res.intent == IntentType.REPORT_INCIDENT
    assert res.confidence >= 0.90
    assert "Cảm ơn" in res.voice_response
    assert res.suggested_action == "RECORD_REPORT"


def test_voice_intent_help_guide():
    service = VoiceIntentService()
    req = VoiceRequest(text="Hướng dẫn sử dụng trợ lý xe máy")
    res = service.parse(req)

    assert res.intent == IntentType.HELP_GUIDE
    assert res.confidence >= 0.90
    assert "Trợ lý Giao thông" in res.voice_response
