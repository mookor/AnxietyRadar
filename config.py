from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


ROOT_DIR = get_app_dir()
load_dotenv(ROOT_DIR / ".env")


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    api_bind_host: str
    api_port: int
    api_client_host: str
    bounds_lat1: float
    bounds_lon1: float
    bounds_lat2: float
    bounds_lon2: float
    max_altitude_m: int
    include_ground: bool
    finder_poll_interval_s: float
    plane_stale_seconds: int
    min_altitude_m: int
    overlay_poll_interval_ms: int

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        return (
            self.bounds_lat1,
            self.bounds_lon1,
            self.bounds_lat2,
            self.bounds_lon2,
        )

    @property
    def api_base_url(self) -> str:
        return f"http://{self.api_client_host}:{self.api_port}"

    @property
    def planes_url(self) -> str:
        return f"{self.api_base_url}/planes"

    @property
    def planes_count_url(self) -> str:
        return f"{self.api_base_url}/planes/count"

    @property
    def health_url(self) -> str:
        return f"{self.api_base_url}/health"


def get_settings() -> Settings:
    return Settings(
        api_bind_host=os.getenv("API_BIND_HOST", "0.0.0.0"),
        api_port=int(os.getenv("API_PORT", "8000")),
        api_client_host=os.getenv("API_CLIENT_HOST", "localhost"),
        bounds_lat1=float(os.getenv("BOUNDS_LAT1", "55.040451")),
        bounds_lon1=float(os.getenv("BOUNDS_LON1", "82.537111")),
        bounds_lat2=float(os.getenv("BOUNDS_LAT2", "54.972320")),
        bounds_lon2=float(os.getenv("BOUNDS_LON2", "82.992117")),
        max_altitude_m=int(os.getenv("MAX_ALTITUDE_M", "20000")),
        include_ground=_env_bool("INCLUDE_GROUND", True),
        finder_poll_interval_s=float(os.getenv("FINDER_POLL_INTERVAL_S", "1")),
        plane_stale_seconds=int(os.getenv("PLANE_STALE_SECONDS", "60")),
        min_altitude_m=int(os.getenv("MIN_ALTITUDE_M", "10")),
        overlay_poll_interval_ms=int(os.getenv("OVERLAY_POLL_INTERVAL_MS", "1500")),
    )
