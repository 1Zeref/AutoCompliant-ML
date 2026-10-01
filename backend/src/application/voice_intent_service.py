"""
Vietnamese Voice Intent Parser and Natural Language Processing Engine.
Classifies rider voice commands into actionable intents with low latency (< 15ms).
"""
import re
from typing import Tuple, Optional
from backend.src.domain.voice import (
    VoiceRequest,
    VoiceResponse,
    VoiceEntities,
    IntentType,
)
from backend.src.core.logger import logger


def normalize_vietnamese_text(text: str) -> str:
    """Lowercases, trims and cleans punctuation for uniform pattern matching."""
    text = text.lower().strip()
    text = re.sub(r"[?!.,:;\"'()\[\]{}]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


class VoiceIntentService:
    def __init__(self):
        # Known POIs in Ho Chi Minh City and Hanoi for quick geocoding
        self.popular_destinations = {
            "chợ bến thành": (10.7725, 106.6980),
            "bến thành": (10.7725, 106.6980),
            "phố đi bộ nguyễn huệ": (10.7744, 106.7038),
            "nguyễn huệ": (10.7744, 106.7038),
            "nhà thờ đức bà": (10.7798, 106.6990),
            "landmark 81": (10.7952, 106.7218),
            "hàng xanh": (10.8018, 106.7115),
            "ngã tư hàng xanh": (10.8018, 106.7115),
            "sân bay tân sơn nhất": (10.8185, 106.6588),
            "tân sơn nhất": (10.8185, 106.6588),
            "hồ gươm": (21.0285, 105.8542),
            "hồ tây": (21.0583, 105.8208),
            "bến xe miền đông": (10.8142, 106.7128),
            "cầu sài gòn": (10.7997, 106.7214),
            "thảo điền": (10.8045, 106.7335),
        }

    def parse(self, request: VoiceRequest) -> VoiceResponse:
        raw_text = request.text
        norm = normalize_vietnamese_text(raw_text)
        logger.info(f"Parsing voice utterance: '{raw_text}' (normalized: '{norm}')")

        intent, confidence, entities, speech, action = self._classify(norm, raw_text)

        return VoiceResponse(
            intent=intent,
            confidence=confidence,
            entities=entities,
            voice_response=speech,
            suggested_action=action,
            metadata={
                "original_text": raw_text,
                "normalized_text": norm,
            },
        )

    def _classify(
        self, norm: str, raw: str
    ) -> Tuple[IntentType, float, VoiceEntities, str, Optional[str]]:
        entities = VoiceEntities()

        # Check flags
        if "tránh ngập" in norm or "không ngập" in norm or "né ngập" in norm:
            entities.avoid_floods = True
        if "tốc độ" in norm or "bắn tốc độ" in norm:
            entities.speed_inquiry = True

        # 1. NAVIGATION INTENT
        nav_patterns = [
            r"chỉ đường (?:tới|đến|về|ra|qua)\s+(.+)",
            r"dẫn đường (?:tới|đến|về|ra|qua)\s+(.+)",
            r"tìm đường (?:tới|đến|về|ra|qua|đi)\s+(.+)",
            r"đi (?:tới|đến|về|ra|qua)\s+(.+)",
            r"đường (?:tới|đến|về|ra|qua)\s+(.+)",
            r"hướng dẫn đường đi\s+(.+)",
        ]

        for pat in nav_patterns:
            m = re.search(pat, norm)
            if m:
                dest = m.group(1).strip()
                # Clean filler words at end
                dest = re.sub(
                    r"\b(tránh ngập|tránh kẹt xe|nhanh nhất|giùm tôi|giúp tôi|nhé|nha|với)\b.*",
                    "",
                    dest,
                ).strip()
                entities.destination = dest.title()

                dest_lower = dest.lower()
                target_coords = self.popular_destinations.get(dest_lower)

                speech = (
                    f"Đang tìm lộ trình xe máy an toàn đến {entities.destination}."
                )
                if entities.avoid_floods:
                    speech += " Đã kích hoạt chế độ tự động né tránh các điểm ngập nước."

                return (
                    IntentType.NAVIGATE,
                    0.96,
                    entities,
                    speech,
                    "START_NAVIGATION",
                )

        # 2. HAZARDS / CAMERA / SPEED INQUIRY
        hazard_patterns = [
            "camera",
            "phạt nguội",
            "bắn tốc độ",
            "chốt giao thông",
            "chốt công an",
            "csgt",
            "biển báo",
            "tốc độ tối đa",
            "giới hạn tốc độ",
            "phía trước có gì",
        ]
        if any(p in norm for p in hazard_patterns):
            entities.hazard_type = "speed_camera"
            speech = (
                "Đang quét các camera phạt nguội và biển báo tốc độ xung quanh vị trí của bạn trong bán kính 500 mét."
            )
            return (
                IntentType.CHECK_HAZARDS,
                0.94,
                entities,
                speech,
                "SCAN_HAZARDS",
            )

        # 3. FLOOD / WEATHER CHECK
        flood_patterns = [
            "ngập",
            "ngập nước",
            "triều cường",
            "nước dâng",
            "mưa",
            "thời tiết",
            "đoạn nào ngập",
        ]
        if any(p in norm for p in flood_patterns):
            entities.hazard_type = "flood_point"
            speech = (
                "Hệ thống đang kiểm tra các điểm ngập úng mùa mưa và triều cường trên tuyến đường bạn đang đi."
            )
            return (
                IntentType.CHECK_FLOOD_WEATHER,
                0.93,
                entities,
                speech,
                "SCAN_FLOODS",
            )

        # 4. REPORT TRAFFIC INCIDENT
        report_patterns = [
            "báo cáo",
            "báo kẹt xe",
            "tai nạn",
            "đang tắc đường",
            "kẹt cứng",
            "đường ngập sâu",
            "có sự cố",
        ]
        if any(p in norm for p in report_patterns):
            speech = (
                "Cảm ơn bạn đã đóng góp thông tin. Trợ lý đã ghi nhận báo cáo giao thông tại vị trí hiện tại của bạn để cảnh báo cho cộng đồng xe máy."
            )
            return (
                IntentType.REPORT_INCIDENT,
                0.91,
                entities,
                speech,
                "RECORD_REPORT",
            )

        # 5. HELP GUIDE
        help_patterns = [
            "giúp",
            "hướng dẫn",
            "làm sao",
            "bạn là ai",
            "chức năng",
            "xin chào",
            "hello",
            "alo",
        ]
        if any(p in norm for p in help_patterns):
            speech = (
                "Tôi là Trợ lý Giao thông Xe máy Việt Nam. Bạn có thể ra lệnh bằng giọng nói: "
                "'Chỉ đường tới Chợ Bến Thành', 'Phía trước có camera không', hoặc 'Xem điểm ngập nước'."
            )
            return (
                IntentType.HELP_GUIDE,
                0.95,
                entities,
                speech,
                "SHOW_HELP",
            )

        # Fallback
        speech = (
            f"Tôi chưa hiểu rõ câu lệnh '{raw}'. Bạn có thể nói 'Chỉ đường tới...', "
            "'Phía trước có camera không?' hoặc 'Đường có ngập không?'."
        )
        return (
            IntentType.UNKNOWN,
            0.50,
            entities,
            speech,
            None,
        )


voice_intent_service = VoiceIntentService()
