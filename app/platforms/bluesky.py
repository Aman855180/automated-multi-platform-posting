"""Bluesky (AT Protocol) platform integration.

Official API Reference: https://docs.bsky.app/docs/category/at-protocol-api
"""

import logging
from datetime import datetime, timezone
from typing import Optional
import httpx

from app.config import Settings, settings as default_settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)


class BlueskyPlatform(BasePlatform):
    """Integrates with Bluesky via the AT Protocol XRPC API."""

    name = "Bluesky"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or default_settings

    async def publish(self, message: str) -> PlatformResult:
        """Create a session and publish a record to the Bluesky feed."""
        handle = self.config.BLUESKY_HANDLE
        password = self.config.BLUESKY_APP_PASSWORD
        service_url = (self.config.BLUESKY_SERVICE_URL or "https://bsky.social").rstrip("/")

        if not handle or not password:
            return self._create_failure_result(
                "Missing credentials: BLUESKY_HANDLE and BLUESKY_APP_PASSWORD must be configured."
            )

        now_utc = datetime.now(timezone.utc)
        iso_created_at = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT_SECONDS) as client:
                # Step 1: Create authenticated session
                session_url = f"{service_url}/xrpc/com.atproto.server.createSession"
                session_payload = {
                    "identifier": handle,
                    "password": password,
                }
                session_resp = await client.post(session_url, json=session_payload)

                if session_resp.status_code == 401:
                    return self._create_failure_result(
                        "Authentication failed: Invalid Bluesky handle or app password."
                    )
                elif session_resp.status_code != 200:
                    return self._create_failure_result(
                        f"Session creation failed (HTTP {session_resp.status_code}): {session_resp.text}"
                    )

                session_data = session_resp.json()
                access_jwt = session_data.get("accessJwt")
                user_did = session_data.get("did")
                resolved_handle = session_data.get("handle") or handle

                if not access_jwt or not user_did:
                    return self._create_failure_result(
                        "Invalid session response from Bluesky: missing accessJwt or did."
                    )

                # Step 2: Create post record in repo
                record_url = f"{service_url}/xrpc/com.atproto.repo.createRecord"
                headers = {
                    "Authorization": f"Bearer {access_jwt}",
                    "Content-Type": "application/json",
                    "User-Agent": "AutomatedMultiPlatformPosting/1.0",
                }
                post_payload = {
                    "repo": user_did,
                    "collection": "app.bsky.feed.post",
                    "record": {
                        "$type": "app.bsky.feed.post",
                        "text": message,
                        "createdAt": iso_created_at,
                    },
                }

                post_resp = await client.post(record_url, json=post_payload, headers=headers)

                if post_resp.status_code in (200, 201):
                    post_data = post_resp.json()
                    # AT-URI format: at://did:plc:xxx/app.bsky.feed.post/3kxxxxxxxxx
                    at_uri = post_data.get("uri", "")
                    rkey = at_uri.split("/")[-1] if "/" in at_uri else ""
                    public_url = (
                        f"https://bsky.app/profile/{resolved_handle}/post/{rkey}"
                        if rkey
                        else None
                    )

                    return self._create_success_result(
                        posted_url=public_url,
                        public_access=True,
                        dt=now_utc,
                    )
                elif post_resp.status_code == 429:
                    return self._create_failure_result("Rate limit exceeded on Bluesky API.")
                else:
                    return self._create_failure_result(
                        f"Post record failed (HTTP {post_resp.status_code}): {post_resp.text}"
                    )

        except httpx.TimeoutException:
            return self._create_failure_result("Request timed out connecting to Bluesky API.")
        except httpx.RequestError as exc:
            return self._create_failure_result(f"Network error connecting to Bluesky: {str(exc)}")
        except Exception as exc:
            logger.exception("Unexpected error in BlueskyPlatform.publish")
            return self._create_failure_result(f"Unexpected error: {str(exc)}")
