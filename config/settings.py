"""중앙 설정 (pydantic-settings). .env에서 타입 안전하게 로드한다."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # API
    dart_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    gemini_fallback_model: str = ""

    # 경로
    data_dir: Path = Path("data/companies")
    config_dir: Path = Path("config")

    # accounting-precision: 금액 round 자릿수 (원화 정수 단위 기본)
    amount_round_digits: int = 0


settings = Settings()
