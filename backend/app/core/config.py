import os
from functools import lru_cache


class Settings:
    def __init__(self) -> None:
        self.app_name: str = os.getenv("APP_NAME", "AlfaHack Backend")
        self.database_url: str = os.getenv("DATABASE_URL", "sqlite:///./data.db")
        self.ml_service_url: str = os.getenv("ML_SERVICE_URL", "http://localhost:8001/score")
        self.debug: bool = os.getenv("DEBUG", "false").lower() == "true"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
