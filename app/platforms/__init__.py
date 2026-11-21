"""Platform integrations registry."""

from app.platforms.base import BasePlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.reddit import RedditPlatform
from app.platforms.linkedin import LinkedInPlatform
from app.platforms.wordpress import WordPressPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.devto import DevToPlatform

__all__ = [
    "BasePlatform",
    "MastodonPlatform",
    "BlueskyPlatform",
    "TelegramPlatform",
    "RedditPlatform",
    "LinkedInPlatform",
    "WordPressPlatform",
    "DiscordPlatform",
    "DevToPlatform",
]
