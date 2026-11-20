"""WordPress REST API platform integration.

Official API Reference:
https://developer.wordpress.org/rest-api/reference/posts/#create-a-post
"""

import logging
from datetime import datetime
from typing import Optional
import httpx

from app.config import Settings, settings as default_settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)


class WordPressPlatform(BasePlatform):
    """Integrates with WordPress official REST API using Application Passwords."""

    name = "WordPress"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or default_settings

    async def publish(self, message: str) -> PlatformResult:
        """Create and publish a post to the configured WordPress site."""
        site_url = (self.config.WORDPRESS_SITE_URL or "").rstrip("/")
        username = self.config.WORDPRESS_USERNAME
        app_password = self.config.WORDPRESS_APP_PASSWORD

        if not site_url or not username or not app_password:
            return self._create_failure_result(
                "Missing credentials: WORDPRESS_SITE_URL, WORDPRESS_USERNAME, and WORDPRESS_APP_PASSWORD must be configured."
            )

        endpoint = f"{site_url}/wp-json/wp/v2/posts"
        title = message if len(message) <= 80 else message[:77] + "..."

        payload = {
            "title": title,
            "content": f"<p>{message}</p>",
            "status": "publish",
        }

        headers = {
            "User-Agent": "AutomatedMultiPlatformPosting/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    auth=(username, app_password),
                )

                if response.status_code == 201:
                    data = response.json()
                    posted_url = data.get("link")
                    raw_date = data.get("date_gmt")
                    dt = None
                    if raw_date:
                        try:
                            dt = datetime.fromisoformat(raw_date)
                        except Exception:
                            dt = None

                    return self._create_success_result(
                        posted_url=posted_url,
                        public_access=True,
                        dt=dt,
                    )
                elif response.status_code in (401, 403):
                    return self._create_failure_result(
                        f"Authentication failed: Invalid credentials or insufficient permissions (HTTP {response.status_code})."
                    )
                else:
                    return self._create_failure_result(
                        f"WordPress API Error (HTTP {response.status_code}): {response.text}"
                    )

        except httpx.TimeoutException:
            return self._create_failure_result("Request timed out connecting to WordPress API.")
        except httpx.RequestError as exc:
            return self._create_failure_result(f"Network error connecting to WordPress: {str(exc)}")
        except Exception as exc:
            logger.exception("Unexpected error in WordPressPlatform.publish")
            return self._create_failure_result(f"Unexpected error: {str(exc)}")
