"""Posting service coordinating concurrent multi-platform publishing."""

import asyncio
import logging
from typing import List, Optional

from app.config import Settings, settings as default_settings
from app.platforms.base import BasePlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.reddit import RedditPlatform
from app.platforms.linkedin import LinkedInPlatform
from app.schemas import PlatformResult, PostingResponse

logger = logging.getLogger(__name__)


class PostingService:
    """Coordinates internal platform discovery and concurrent message publishing."""

    def __init__(
        self,
        platforms: Optional[List[BasePlatform]] = None,
        config: Optional[Settings] = None,
    ):
        self.config = config or default_settings
        # If platforms list not explicitly injected (e.g. for testing), load default 5 platforms
        if platforms is not None:
            self.platforms = platforms
        else:
            self.platforms = self._get_default_platforms()

    def _get_default_platforms(self) -> List[BasePlatform]:
        """Instantiate the 5 default target platforms according to assignment specification."""
        return [
            MastodonPlatform(config=self.config),
            BlueskyPlatform(config=self.config),
            TelegramPlatform(config=self.config),
            RedditPlatform(config=self.config),
            LinkedInPlatform(config=self.config),
        ]

    async def _publish_to_platform(
        self, platform: BasePlatform, message: str
    ) -> PlatformResult:
        """Execute publishing for a single platform guarded by timeout and exception boundary."""
        try:
            # Enforce an outer timeout per platform task
            timeout = self.config.REQUEST_TIMEOUT_SECONDS + 2.0
            return await asyncio.wait_for(platform.publish(message), timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning("Timeout occurred publishing to %s", platform.name)
            return PlatformResult(
                platform=platform.name,
                status="failed",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Publishing operation to {platform.name} timed out.",
            )
        except Exception as exc:
            logger.exception("Unexpected exception publishing to %s", platform.name)
            return PlatformResult(
                platform=platform.name,
                status="failed",
                posted_url=None,
                public_access=False,
                date=None,
                time=None,
                error=f"Internal publishing error: {str(exc)}",
            )

    async def publish_message(self, message: str) -> PostingResponse:
        """Publish the validated message to all selected platforms concurrently.

        Args:
            message: Validated message string with exactly one CTA URL.

        Returns:
            PostingResponse: Consolidated results across all platforms.
        """
        logger.info(
            "Initiating concurrent publishing across %d platforms...",
            len(self.platforms),
        )

        # Create concurrent publishing tasks
        tasks = [
            self._publish_to_platform(platform, message)
            for platform in self.platforms
        ]

        # Execute concurrently with return_exceptions=True
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        results: List[PlatformResult] = []
        for i, raw in enumerate(raw_results):
            if isinstance(raw, PlatformResult):
                results.append(raw)
            elif isinstance(raw, Exception):
                platform_name = self.platforms[i].name
                results.append(
                    PlatformResult(
                        platform=platform_name,
                        status="failed",
                        posted_url=None,
                        public_access=False,
                        date=None,
                        time=None,
                        error=f"Unhandled platform error: {str(raw)}",
                    )
                )

        # Overall success is True only if every configured platform succeeded
        overall_success = all(res.status == "success" for res in results) if results else False

        logger.info(
            "Concurrent publishing finished. Overall success: %s (%d succeeded, %d failed)",
            overall_success,
            sum(1 for r in results if r.status == "success"),
            sum(1 for r in results if r.status == "failed"),
        )

        return PostingResponse(
            success=overall_success,
            results=results,
        )
