"""LinkedIn Posts API platform integration.

Official API Reference:
https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import httpx

from app.config import Settings, settings as default_settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)


class LinkedInPlatform(BasePlatform):
    """Integrates with LinkedIn's official Posts API to publish updates to Member/Org feeds."""

    name = "LinkedIn"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or default_settings

    async def publish(self, message: str) -> PlatformResult:
        """Publish a text post with commentary to LinkedIn."""
        access_token = self.config.LINKEDIN_ACCESS_TOKEN
        author_urn = self.config.LINKEDIN_AUTHOR_URN

        if not access_token or not author_urn:
            return self._create_failure_result(
                "Missing credentials: LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN must be configured."
            )

        endpoint = "https://api.linkedin.com/rest/posts"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "202401",
            "User-Agent": "AutomatedMultiPlatformPosting/1.0",
        }

        payload = {
            "author": author_urn,
            "commentary": message,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": [],
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False,
        }

        now_utc = datetime.now(timezone.utc)

        try:
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(endpoint, json=payload, headers=headers)

                data: Dict[str, Any] = {}
                try:
                    data = response.json()
                except Exception:
                    pass

                if response.status_code == 201:
                    post_urn = (
                        response.headers.get("x-restli-id")
                        or response.headers.get("x-linkedin-id")
                        or data.get("id")
                    )

                    posted_url = (
                        f"https://www.linkedin.com/feed/update/{post_urn}"
                        if post_urn
                        else "https://www.linkedin.com/feed/"
                    )

                    return self._create_success_result(
                        posted_url=posted_url,
                        public_access=True,
                        dt=now_utc,
                    )
                elif response.status_code == 401:
                    return self._create_failure_result(
                        "Authentication failed: Invalid or expired LinkedIn access token."
                    )
                elif response.status_code == 403:
                    return self._create_failure_result(
                        "Permission denied: Missing required 'w_member_social' or organization permission."
                    )
                elif response.status_code == 429:
                    return self._create_failure_result("Rate limit exceeded on LinkedIn API.")
                elif response.status_code in (400, 422):
                    err_msg = data.get("message") or response.text
                    return self._create_failure_result(f"LinkedIn request error: {err_msg}")
                else:
                    return self._create_failure_result(
                        f"LinkedIn API Error (HTTP {response.status_code}): {response.text}"
                    )

        except httpx.TimeoutException:
            return self._create_failure_result("Request timed out connecting to LinkedIn API.")
        except httpx.RequestError as exc:
            return self._create_failure_result(f"Network error connecting to LinkedIn: {str(exc)}")
        except Exception as exc:
            logger.exception("Unexpected error in LinkedInPlatform.publish")
            return self._create_failure_result(f"Unexpected error: {str(exc)}")
