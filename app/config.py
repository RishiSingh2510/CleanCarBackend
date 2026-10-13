import os
from dataclasses import dataclass, field
from functools import lru_cache


def _bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    return default if v is None else v.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    cors_origins: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()
        )
    )
    session_days: int = field(default_factory=lambda: _int("SESSION_DAYS", 30))
    slot_capacity: int = field(default_factory=lambda: _int("SLOT_CAPACITY", 3))
    booking_window_days: int = field(
        default_factory=lambda: _int("BOOKING_WINDOW_DAYS", 30)
    )
    min_lead_minutes: int = field(default_factory=lambda: _int("MIN_LEAD_MINUTES", 0))
    max_vehicles_per_user: int = field(default_factory=lambda: _int("MAX_VEHICLES", 10))
    seed_demo: bool = field(default_factory=lambda: _bool("SEED_DEMO", False))

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
