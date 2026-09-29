"""Minimal settings for the data collectors.

Reads backend/.env (run commands from backend/). DATA_ROOT defaults to D:/litigia-data.
"""

from os import getenv
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # Haiku solves the PJN captcha
    anthropic_api_key: str = ""
    anthropic_workspace_id: str = ""   # only for keys not scoped to a workspace

    # Vultr — only for scrapers/deploy_parallel.py
    vultr_api_key: str = ""

    # TypeSafe (Jev) — labeling. Pinned version: thresholds are tuned per model version.
    typesafe_api_key: str = ""
    typesafe_model: str = "jev-1.13.0"

    data_root: Path = Path(getenv("DATA_ROOT", "D:/litigia-data"))

    # SAIJ (HuggingFace, updated daily upstream)
    saij_dataset: str = "marianbasti/jurisprudencia-Argentina-SAIJ"
    saij_min_text_length: int = 100

    @property
    def data_raw(self) -> Path:
        return self.data_root / "raw"

    @property
    def data_clean(self) -> Path:
        return self.data_root / "clean"

    @property
    def data_logs(self) -> Path:
        return self.data_root / "logs"

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        # backend/.env wins over OS environment variables: the project's keys are the source of truth
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    def ensure_dirs(self) -> None:
        """Create all data directories if they don't exist."""
        for d in [self.data_root, self.data_raw, self.data_clean, self.data_logs]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
