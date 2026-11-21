"""Discord Webhook platform integration.

Official API Reference:
https://discord.com/developers/docs/resources/webhook#execute-webhook
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
import httpx

from app.config import Settings, settings as default_settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)


class DiscordPlatform(BasePlatform):
    """Integrates with Discord's official Execute Webhook API."""

    name = "Discord"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or default_settings

    async def publish(self, message: str) -> PlatformResult:
        """Publish a message to a Discord channel via official Webhook with wait=true."""
        webhook_url = self.config.DISCORD_WEBHOOK_URL

        if not webhook_url or not webhook_url.strip():
            return self._create_failure_result(
                "Missing credentials: DISCORD_WEBHOOK_URL must be configured."
            )

        # Discord execute webhook endpoint accepts ?wait=true to return the created message object
        clean_url = webhook_url.strip()
        separator = "&" if "?" in clean_url else "?"
        endpoint = f"{clean_url}{separator}wait=true"

        payload = {
            "content": message,
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "AutomatedMultiPlatformPosting/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(endpoint, json=payload, headers=headers)

                data: Dict[str, Any] = {}
                try:
                    data = response.json()
                except Exception:
                    pass

                if response.status_code in (200, 201):
                    message_id = data.get("id")
                    channel_id = data.get("channel_id")
                    guild_id = data.get("guild_id") or self.config.DISCORD_SERVER_ID or "@me"
                    raw_timestamp = data.get("timestamp")

                    dt = None
                    if raw_timestamp:
                        try:
                            dt = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
                        except Exception:
                            dt = None

                    # Construct message permalink
                    posted_url = (
                        f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
                        if message_id and channel_id
                        else None
                    )

                    return self._create_success_result(
                        posted_url=posted_url,
                        public_access=True,
                        dt=dt,
                    )
                elif response.status_code in (401, 404):
                    return self._create_failure_result(
                        "Authentication failed: Invalid or expired Discord webhook URL."
                    )
                elif response.status_code == 429:
                    return self._create_failure_result("Rate limit exceeded on Discord Webhook API.")
                else:
                    err_msg = data.get("message") or response.text
                    return self._create_failure_result(
                        f"Discord API Error (HTTP {response.status_code}): {err_msg}"
                    )

        except httpx.TimeoutException:
            return self._create_failure_result("Request timed out connecting to Discord API.")
        except httpx.RequestError as exc:
            return self._create_failure_result(f"Network error connecting to Discord: {str(exc)}")
        except Exception as exc:
            logger.exception("Unexpected error in DiscordPlatform.publish")
            return self._create_failure_result(f"Unexpected error: {str(exc)}")
