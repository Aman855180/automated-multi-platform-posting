"""Abstract base class and contract for all third-party platform integrations."""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from app.schemas import PlatformResult


class BasePlatform(ABC):
    """Abstract Base Class defining the contract for social/publishing platforms."""

    name: str = "BasePlatform"

    @abstractmethod
    async def publish(self, message: str) -> PlatformResult:
        """Publish content to the platform asynchronously.

        Args:
            message: The validated text message containing exactly one CTA link.

        Returns:
            PlatformResult: Structured result including status, posted_url, and timestamps.
        """
        pass

    def _format_datetime(self, dt: Optional[datetime] = None) -> tuple[str, str]:
        """Return standardized (date_str, time_str) in YYYY-MM-DD and HH:MM:SS formats."""
        now = dt or datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S")

    def _create_success_result(
        self,
        posted_url: Optional[str],
        public_access: bool = True,
        dt: Optional[datetime] = None,
    ) -> PlatformResult:
        """Helper to create a normalized successful PlatformResult."""
        date_str, time_str = self._format_datetime(dt)
        return PlatformResult(
            platform=self.name,
            status="success",
            posted_url=posted_url,
            public_access=public_access,
            date=date_str,
            time=time_str,
            error=None,
        )

    def _create_failure_result(
        self,
        error_message: str,
        dt: Optional[datetime] = None,
    ) -> PlatformResult:
        """Helper to create a normalized failed PlatformResult."""
        # For failed results, date and time can be None or capture timestamp of failure
        # per PDF sample: "date": null, "time": null for failed platforms
        return PlatformResult(
            platform=self.name,
            status="failed",
            posted_url=None,
            public_access=False,
            date=None,
            time=None,
            error=error_message,
        )
