"""Reddit API platform integration.

Official API Reference:
- OAuth2: https://github.com/reddit-archive/reddit/wiki/OAuth2
- Submit: https://www.reddit.com/dev/api#POST_api_submit
"""

import logging
from datetime import datetime, timezone
from typing import Optional
import httpx

from app.config import Settings, settings as default_settings
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult

logger = logging.getLogger(__name__)


class RedditPlatform(BasePlatform):
    """Integrates with Reddit's official API to submit posts to a subreddit."""

    name = "Reddit"

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or default_settings

    async def publish(self, message: str) -> PlatformResult:
        """Authenticate via OAuth2 and submit a self-post to the configured subreddit."""
        client_id = self.config.REDDIT_CLIENT_ID
        client_secret = self.config.REDDIT_CLIENT_SECRET
        username = self.config.REDDIT_USERNAME
        password = self.config.REDDIT_PASSWORD
        subreddit = self.config.REDDIT_SUBREDDIT or "test"
        user_agent = self.config.REDDIT_USER_AGENT or "automated-posting:v1.0.0"

        if not all([client_id, client_secret, username, password]):
            return self._create_failure_result(
                "Missing credentials: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, "
                "REDDIT_USERNAME, and REDDIT_PASSWORD must be configured."
            )

        now_utc = datetime.now(timezone.utc)

        try:
            async with httpx.AsyncClient(timeout=self.config.REQUEST_TIMEOUT_SECONDS) as client:
                # Step 1: Obtain OAuth2 Bearer Access Token
                token_url = "https://www.reddit.com/api/v1/access_token"
                token_auth = (client_id, client_secret)
                token_data = {
                    "grant_type": "password",
                    "username": username,
                    "password": password,
                }
                token_headers = {"User-Agent": user_agent}

                token_resp = await client.post(
                    token_url,
                    auth=token_auth,
                    data=token_data,
                    headers=token_headers,
                )

                if token_resp.status_code == 401:
                    return self._create_failure_result(
                        "Authentication failed: Invalid Reddit client ID or client secret."
                    )

                token_json = token_resp.json()
                if "error" in token_json:
                    return self._create_failure_result(
                        f"Authentication failed: {token_json.get('error')} ({token_json.get('message', '')})"
                    )

                access_token = token_json.get("access_token")
                if not access_token:
                    return self._create_failure_result(
                        "OAuth response missing access_token from Reddit."
                    )

                # Step 2: Submit Post to Subreddit
                submit_url = "https://oauth.reddit.com/api/submit"
                submit_headers = {
                    "Authorization": f"bearer {access_token}",
                    "User-Agent": user_agent,
                }

                # Construct post title (Reddit requires a title; truncate message if long)
                title = message if len(message) <= 80 else message[:77] + "..."

                submit_payload = {
                    "api_type": "json",
                    "kind": "self",
                    "sr": subreddit,
                    "title": title,
                    "text": message,
                    "sendreplies": True,
                }

                submit_resp = await client.post(
                    submit_url,
                    headers=submit_headers,
                    data=submit_payload,
                )

                if submit_resp.status_code == 429:
                    return self._create_failure_result("Rate limit exceeded on Reddit API.")
                elif submit_resp.status_code != 200:
                    return self._create_failure_result(
                        f"Submit failed (HTTP {submit_resp.status_code}): {submit_resp.text}"
                    )

                submit_data = submit_resp.json()
                json_body = submit_data.get("json", {})
                errors = json_body.get("errors", [])
                if errors:
                    error_desc = "; ".join([str(e) for e in errors])
                    return self._create_failure_result(f"Reddit submission error: {error_desc}")

                data_fields = json_body.get("data", {})
                posted_url = data_fields.get("url")

                # Public subreddits are viewable by anyone on the internet
                return self._create_success_result(
                    posted_url=posted_url,
                    public_access=True,
                    dt=now_utc,
                )

        except httpx.TimeoutException:
            return self._create_failure_result("Request timed out connecting to Reddit API.")
        except httpx.RequestError as exc:
            return self._create_failure_result(f"Network error connecting to Reddit: {str(exc)}")
        except Exception as exc:
            logger.exception("Unexpected error in RedditPlatform.publish")
            return self._create_failure_result(f"Unexpected error: {str(exc)}")
