"""Configuration loaded from environment / .env file.

Author: Thanh Nguyen <thanhglobalist@gmail.com>
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Values are read from environment variables (with optional .env file).
    See .env.example for a full reference.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(default="", description="Telegram bot token from @BotFather")
    admin_user_id: int = Field(default=0, description="Telegram numeric ID of the bootstrap admin")
    bridge_public_url: str = Field(default="https://bot.example.com")
    db_path: str = Field(default="/var/lib/sltp-tg-bot/sltp.db")
    listen_host: str = Field(default="127.0.0.1")
    listen_port: int = Field(default=8080)
    log_level: str = Field(default="INFO")
    job_timeout_seconds: int = Field(default=30)
    heartbeat_timeout_seconds: int = Field(default=15)

    def db_dir(self) -> Path:
        return Path(self.db_path).expanduser().parent


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings_cache() -> None:
    """Clear the cached settings (useful in tests)."""
    global _settings
    _settings = None
