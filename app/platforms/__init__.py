"""Platform integrations registry."""

from app.platforms.base import BasePlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.devto import DevToPlatform

__all__ = [
    "BasePlatform",
    "MastodonPlatform",
    "BlueskyPlatform",
    "TelegramPlatform",
    "DiscordPlatform",
    "DevToPlatform",
]
