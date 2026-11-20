"""Application Configuration using Pydantic Settings."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Server settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 4000
    APP_ENV: str = "development"
    REQUEST_TIMEOUT_SECONDS: float = 10.0

    # Mastodon
    MASTODON_INSTANCE_URL: str = "https://mastodon.social"
    MASTODON_ACCESS_TOKEN: Optional[str] = None

    # Bluesky
    BLUESKY_HANDLE: Optional[str] = None
    BLUESKY_APP_PASSWORD: Optional[str] = None
    BLUESKY_SERVICE_URL: str = "https://bsky.social"

    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    TELEGRAM_CHANNEL_USERNAME: Optional[str] = None

    # Reddit
    REDDIT_CLIENT_ID: Optional[str] = None
    REDDIT_CLIENT_SECRET: Optional[str] = None
    REDDIT_USERNAME: Optional[str] = None
    REDDIT_PASSWORD: Optional[str] = None
    REDDIT_SUBREDDIT: str = "test"
    REDDIT_USER_AGENT: str = "automated-posting:v1.0.0"

    # LinkedIn
    LINKEDIN_ACCESS_TOKEN: Optional[str] = None
    LINKEDIN_AUTHOR_URN: Optional[str] = None

    # WordPress (Alternative / Extensible)
    WORDPRESS_SITE_URL: Optional[str] = None
    WORDPRESS_USERNAME: Optional[str] = None
    WORDPRESS_APP_PASSWORD: Optional[str] = None


# Global settings singleton
settings = Settings()
