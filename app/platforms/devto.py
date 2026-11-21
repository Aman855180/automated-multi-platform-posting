"""Dev.to (Forem) API integration."""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from app.config import Settings, settings as default_settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)


class DevToPlatform(BasePlatform):
    """Dev.to publishing integration via official Forem REST API."""

    name = "Dev.to"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or default_settings

    def is_configured(self) -> bool:
        """Return True if Dev.to API Key is configured."""
        api_key = self.config.DEVTO_API_KEY
        return bool(api_key and api_key.strip())

    async def publish(self, message: str) -> PlatformResult:
        """Publish an article to Dev.to via POST https://dev.to/api/articles."""
        if not self.is_configured():
            return self._create_failure_result(
                "Missing credentials: DEVTO_API_KEY must be configured in .env"
            )

        endpoint = "https://dev.to/api/articles"
        headers = {
            "api-key": self.config.DEVTO_API_KEY.strip(),
            "Content-Type": "application/json",
            "Accept": "application/vnd.forem.api-v1+json",
            "User-Agent": "automated-posting:v1.0.0",
        }

        # Dev.to articles require a title
        # Create a concise title from the message or a default
        title_snippet = message.split("http")[0].strip().rstrip(".!?")
        if len(title_snippet) > 60:
            title_snippet = title_snippet[:57] + "..."
        if not title_snippet:
            title_snippet = "Automated Multi-Platform Update"

        payload = {
            "article": {
                "title": title_snippet,
                "published": True,
                "body_markdown": message,
                "tags": ["automation", "python"],
            }
        }

        timeout = httpx.Timeout(self.config.REQUEST_TIMEOUT_SECONDS)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(endpoint, json=payload, headers=headers)

            if response.status_code in (200, 201):
                data = response.json()
                post_url = data.get("url")
                raw_created = data.get("published_at") or data.get("created_at")

                dt = None
                if raw_created:
                    try:
                        clean_ts = raw_created.replace("Z", "+00:00")
                        dt = datetime.fromisoformat(clean_ts)
                    except Exception:
                        dt = datetime.now(timezone.utc)

                logger.info("Successfully published to Dev.to: %s", post_url)
                return self._create_success_result(
                    posted_url=post_url,
                    public_access=True,
                    dt=dt,
                )

            # Error handling
            error_msg = f"Dev.to API error (HTTP {response.status_code}): {response.text}"
            logger.error(error_msg)
            return self._create_failure_result(error_msg)

        except httpx.TimeoutException:
            logger.error("Timeout publishing to Dev.to")
            return self._create_failure_result(
                f"Request to Dev.to timed out after {self.config.REQUEST_TIMEOUT_SECONDS}s"
            )
        except Exception as exc:
            logger.exception("Unexpected error publishing to Dev.to")
            return self._create_failure_result(
                f"Unexpected error publishing to Dev.to: {str(exc)}"
            )
