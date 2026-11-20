"""Telegram Bot API platform integration.

Official API Reference: https://core.telegram.org/bots/api#sendmessage
"""

import logging
from datetime import datetime, timezone
from typing import Optional
import httpx

from app.config import Settings, settings as default_settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)


class TelegramPlatform(BasePlatform):
    """Integrates with Telegram Bot API to publish updates to channels/chats."""

    name = "Telegram"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or default_settings

    async def publish(self, message: str) -> PlatformResult:
        """Send a message to a Telegram channel or chat via the Telegram Bot API."""
        bot_token = self.config.TELEGRAM_BOT_TOKEN
        chat_id = self.config.TELEGRAM_CHAT_ID

        if not bot_token or not chat_id:
            return self._create_failure_result(
                "Missing credentials: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured."
            )

        endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "disable_web_page_preview": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(endpoint, json=payload)
                data = response.json()

                if response.status_code == 200 and data.get("ok"):
                    result_obj = data.get("result", {})
                    message_id = result_obj.get("message_id")
                    chat_obj = result_obj.get("chat", {})
                    timestamp_unix = result_obj.get("date")

                    dt = None
                    if timestamp_unix:
                        try:
                            dt = datetime.fromtimestamp(timestamp_unix, tz=timezone.utc)
                        except Exception:
                            dt = None

                    # Determine public web access and URL
                    # Telegram channels with a public username can be viewed at https://t.me/<username>/<message_id>
                    channel_username = (
                        chat_obj.get("username")
                        or self.config.TELEGRAM_CHANNEL_USERNAME
                    )
                    if channel_username:
                        # Strip leading @ if present
                        clean_username = channel_username.lstrip("@")
                        posted_url = f"https://t.me/{clean_username}/{message_id}"
                        public_access = True
                    else:
                        # Private group or channel without public username
                        posted_url = None
                        public_access = False

                    return self._create_success_result(
                        posted_url=posted_url,
                        public_access=public_access,
                        dt=dt,
                    )
                elif response.status_code == 401 or not data.get("ok", True) and "Unauthorized" in data.get("description", ""):
                    return self._create_failure_result(
                        f"Authentication failed: {data.get('description', 'Invalid Telegram bot token')}"
                    )
                elif response.status_code == 429:
                    return self._create_failure_result("Rate limit exceeded on Telegram Bot API.")
                else:
                    description = data.get("description", response.text)
                    return self._create_failure_result(
                        f"Telegram API Error (HTTP {response.status_code}): {description}"
                    )

        except httpx.TimeoutException:
            return self._create_failure_result("Request timed out connecting to Telegram API.")
        except httpx.RequestError as exc:
            return self._create_failure_result(f"Network error connecting to Telegram: {str(exc)}")
        except Exception as exc:
            logger.exception("Unexpected error in TelegramPlatform.publish")
            return self._create_failure_result(f"Unexpected error: {str(exc)}")
