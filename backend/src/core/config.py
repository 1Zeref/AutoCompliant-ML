"""
Core Configuration Module for Vietnam Motorbike Smart Traffic Assistant.
Loads settings from environment variables with safe defaults.
"""
import os
from typing import List
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Automatically load .env if available, or .env.dev as fallback
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists(".env.dev"):
    load_dotenv(".env.dev")
else:
    load_dotenv()


@dataclass
class Settings:
    app_name: str = os.getenv("APP_NAME", "Vietnam Motorbike Smart Traffic Assistant")
    app_env: str = os.getenv("APP_ENV", "development")
    app_port: int = int(os.getenv("APP_PORT", "8000"))
    debug: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
    host: str = os.getenv("HOST", "0.0.0.0")
    secret_key: str = os.getenv("SECRET_KEY", "default-dev-secret-key-32-chars-ok")
    allowed_origins: List[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
            if origin.strip()
        ]
    )
    osrm_server_url: str = os.getenv("OSRM_SERVER_URL", "https://router.project-osrm.org")
    default_city: str = os.getenv("DEFAULT_CITY", "Ho_Chi_Minh")
    default_latitude: float = float(os.getenv("DEFAULT_LATITUDE", "10.7769"))
    default_longitude: float = float(os.getenv("DEFAULT_LONGITUDE", "106.7009"))
    hazard_default_radius_meters: float = float(os.getenv("HAZARD_DEFAULT_RADIUS_METERS", "300"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_format: str = os.getenv("LOG_FORMAT", "json")
    version: str = "1.0.0"


settings = Settings()
