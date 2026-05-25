"""Runtime configuration, loaded from environment / .env at the repo root."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]  # .../cs2-pickems
BACKEND_DIR = Path(__file__).resolve().parents[1]  # .../cs2-pickems/backend


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # Odds provider
    odds_api_key: str = ""
    odds_provider: str = "oddspapi"  # oddspapi | theoddsapi | none

    # Liquipedia API politeness
    liquipedia_user_agent: str = "cs2-pickems/0.1 (https://github.com/local)"

    # Monte Carlo
    sim_count_quick: int = 10_000
    sim_count_full: int = 100_000

    @property
    def data_dir(self) -> Path:
        return REPO_ROOT / "data"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"


settings = Settings()
