"""Mastodon API platform integration.

Official API Reference: https://docs.joinmastodon.org/methods/statuses/#create
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
import httpx

from app.config import Settings, settings as default_settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)


class MastodonPlatform(BasePlatform):
    """Integrates with Mastodon's Statuses API to post public updates."""

    name = "Mastodon"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or default_settings

    async def publish(self, message: str) -> PlatformResult:
        """Publish a status update to the configured Mastodon instance."""
        instance_url = (self.config.MASTODON_INSTANCE_URL or "").rstrip("/")
        access_token = self.config.MASTODON_ACCESS_TOKEN

        if not instance_url or not access_token:
            return self._create_failure_result(
                "Missing credentials: MASTODON_INSTANCE_URL and MASTODON_ACCESS_TOKEN must be configured."
            )

        endpoint = f"{instance_url}/api/v1/statuses"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "User-Agent": "AutomatedMultiPlatformPosting/1.0",
        }
        payload = {
            "status": message,
            "visibility": "public",
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
                    posted_url = data.get("url") or data.get("uri")
                    created_at_raw = data.get("created_at")
                    dt = None
                    if created_at_raw:
                        try:
                            dt = datetime.fromisoformat(created_at_raw.replace("Z", "+00:00"))
                        except Exception:
                            dt = None

                    visibility = data.get("visibility", "public")
                    is_public = visibility in ("public", "unlisted")

                    return self._create_success_result(
                        posted_url=posted_url,
                        public_access=is_public,
                        dt=dt,
                    )
                elif response.status_code == 401:
                    return self._create_failure_result(
                        "Authentication failed: Invalid or expired Mastodon access token."
                    )
                elif response.status_code == 403:
                    return self._create_failure_result(
                        "Permission denied: Access token lacks required 'write:statuses' scope."
                    )
                elif response.status_code == 422:
                    error_detail = data.get("error", response.text)
                    return self._create_failure_result(f"Unprocessable entity: {error_detail}")
                elif response.status_code == 429:
                    return self._create_failure_result("Rate limit exceeded on Mastodon instance.")
                else:
                    return self._create_failure_result(
                        f"API Error (HTTP {response.status_code}): {response.text}"
                    )

        except httpx.TimeoutException:
            return self._create_failure_result("Request timed out connecting to Mastodon API.")
        except httpx.RequestError as exc:
            return self._create_failure_result(f"Network error connecting to Mastodon: {str(exc)}")
        except Exception as exc:
            logger.exception("Unexpected error in MastodonPlatform.publish")
            return self._create_failure_result(f"Unexpected error: {str(exc)}")
