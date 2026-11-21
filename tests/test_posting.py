"""Integration and concurrency tests for the /posting endpoint and PostingService."""

import asyncio
from unittest.mock import AsyncMock, patch
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, posting_service
from app.platforms.base import BasePlatform
from app.schemas import PlatformResult
from app.services.posting_service import PostingService


client = TestClient(app)


# Mock Platform helper for isolated concurrency testing
class MockPlatform(BasePlatform):
    def __init__(
        self,
        name: str,
        status: str = "success",
        posted_url: str = None,
        public_access: bool = True,
        error: str = None,
        delay: float = 0.0,
        raise_exception: bool = False,
    ):
        self.name = name
        self._status = status
        self._posted_url = posted_url
        self._public_access = public_access
        self._error = error
        self._delay = delay
        self._raise_exception = raise_exception

    async def publish(self, message: str) -> PlatformResult:
        if self._delay > 0:
            await asyncio.sleep(self._delay)
        if self._raise_exception:
            raise RuntimeError(f"Unexpected crash in {self.name}")
        if self._status == "success":
            return self._create_success_result(
                posted_url=self._posted_url or f"https://{self.name.lower()}.example.com/post/1",
                public_access=self._public_access,
            )
        return self._create_failure_result(self._error or "Mock error")


def test_health_check_endpoint():
    """Ensure health endpoint returns operational status and platform names."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["target_platforms_count"] >= 5
    assert "Mastodon" in data["target_platforms"]
    assert "Bluesky" in data["target_platforms"]
    assert "Telegram" in data["target_platforms"]
    assert "Discord" in data["target_platforms"]
    assert "Dev.to" in data["target_platforms"]


def test_posting_endpoint_validation_errors():
    """Ensure HTTP 422 is returned for invalid payloads."""
    # Empty message
    r1 = client.post("/posting", json={"message": ""})
    assert r1.status_code == 422

    # Exceeding 200 chars
    r2 = client.post("/posting", json={"message": "A" * 190 + " https://example.com"})
    assert r2.status_code == 422

    # No URL
    r3 = client.post("/posting", json={"message": "Hello world with no CTA"})
    assert r3.status_code == 422

    # Multiple URLs
    r4 = client.post(
        "/posting",
        json={"message": "Link 1: https://a.com Link 2: https://b.com"},
    )
    assert r4.status_code == 422


@pytest.mark.asyncio
async def test_posting_service_all_success():
    """Ensure PostingService reports overall success=True when all platforms succeed."""
    mock_platforms = [
        MockPlatform("Mastodon", status="success", posted_url="https://mastodon.social/@u/1"),
        MockPlatform("Bluesky", status="success", posted_url="https://bsky.app/profile/u/post/1"),
        MockPlatform("Telegram", status="success", posted_url="https://t.me/channel/1"),
        MockPlatform("Discord", status="success", posted_url="https://discord.com/channels/1/2/3"),
        MockPlatform("Dev.to", status="success", posted_url="https://dev.to/user/post-1"),
    ]
    service = PostingService(platforms=mock_platforms)
    response = await service.publish_message("Check our new site https://example.com")

    assert response.success is True
    assert len(response.results) == 5
    for r in response.results:
        assert r.status == "success"
        assert r.posted_url is not None
        assert r.public_access is True
        assert r.date is not None
        assert r.time is not None
        assert r.error is None


@pytest.mark.asyncio
async def test_posting_service_partial_failure():
    """Ensure partial failure accurately yields success=False and does not affect other platforms."""
    mock_platforms = [
        MockPlatform("Mastodon", status="success", posted_url="https://mastodon.social/@u/1"),
        MockPlatform("Bluesky", status="failed", error="Authentication failed: Invalid credentials"),
        MockPlatform("Telegram", status="success", posted_url="https://t.me/channel/1"),
        MockPlatform("Discord", status="failed", error="Rate limit exceeded"),
        MockPlatform("Dev.to", status="success", posted_url="https://dev.to/user/post-1"),
    ]
    service = PostingService(platforms=mock_platforms)
    response = await service.publish_message("Check our new site https://example.com")

    # Partial success MUST NOT be reported as complete success
    assert response.success is False
    assert len(response.results) == 5

    results_by_name = {r.platform: r for r in response.results}
    assert results_by_name["Mastodon"].status == "success"
    assert results_by_name["Bluesky"].status == "failed"
    assert results_by_name["Bluesky"].error == "Authentication failed: Invalid credentials"
    assert results_by_name["Telegram"].status == "success"
    assert results_by_name["Discord"].status == "failed"
    assert results_by_name["Dev.to"].status == "success"


@pytest.mark.asyncio
async def test_posting_service_all_failure():
    """Ensure service handles scenario where all platforms fail."""
    mock_platforms = [
        MockPlatform("Mastodon", status="failed", error="Missing credentials"),
        MockPlatform("Bluesky", status="failed", error="Missing credentials"),
        MockPlatform("Telegram", status="failed", error="Missing credentials"),
        MockPlatform("Discord", status="failed", error="Missing credentials"),
        MockPlatform("Dev.to", status="failed", error="Missing credentials"),
    ]
    service = PostingService(platforms=mock_platforms)
    response = await service.publish_message("Check our new site https://example.com")

    assert response.success is False
    assert len(response.results) == 5
    for r in response.results:
        assert r.status == "failed"
        assert r.posted_url is None
        assert r.error == "Missing credentials"


@pytest.mark.asyncio
async def test_platform_timeout_resilience():
    """Ensure a slow platform timing out does not block or fail remaining platforms."""
    mock_platforms = [
        MockPlatform("FastPlatform1", status="success", delay=0.01),
        MockPlatform("SlowPlatform", status="success", delay=15.0),  # Will exceed timeout
        MockPlatform("FastPlatform2", status="success", delay=0.01),
    ]

    # Configure a 0.2 second timeout for this test
    from app.config import Settings
    fast_timeout_settings = Settings(REQUEST_TIMEOUT_SECONDS=0.1)

    service = PostingService(platforms=mock_platforms, config=fast_timeout_settings)
    response = await service.publish_message("Check our new site https://example.com")

    assert response.success is False
    results_by_name = {r.platform: r for r in response.results}
    assert results_by_name["FastPlatform1"].status == "success"
    assert results_by_name["FastPlatform2"].status == "success"
    assert results_by_name["SlowPlatform"].status == "failed"
    assert "timed out" in (results_by_name["SlowPlatform"].error or "")


@pytest.mark.asyncio
async def test_unhandled_exception_isolation():
    """Ensure an unhandled crash inside one platform does not bring down the service."""
    mock_platforms = [
        MockPlatform("PlatformA", status="success"),
        MockPlatform("CrashingPlatform", raise_exception=True),
        MockPlatform("PlatformB", status="success"),
    ]
    service = PostingService(platforms=mock_platforms)
    response = await service.publish_message("Check our new site https://example.com")

    assert response.success is False
    results_by_name = {r.platform: r for r in response.results}
    assert results_by_name["PlatformA"].status == "success"
    assert results_by_name["PlatformB"].status == "success"
    assert results_by_name["CrashingPlatform"].status == "failed"
    assert "Unexpected crash" in (results_by_name["CrashingPlatform"].error or "")


def test_endpoint_end_to_end_with_injected_service():
    """Test full FastAPI endpoint invocation with custom mock platforms."""
    custom_platforms = [
        MockPlatform("Mastodon", status="success", posted_url="https://mastodon.social/@demo/1"),
        MockPlatform("Bluesky", status="success", posted_url="https://bsky.app/profile/demo/post/1"),
        MockPlatform("Telegram", status="success", posted_url="https://t.me/demo/1"),
        MockPlatform("Discord", status="success", posted_url="https://discord.com/channels/1/2/3"),
        MockPlatform("Dev.to", status="success", posted_url="https://dev.to/demo/1"),
    ]

    with patch.object(posting_service, "platforms", custom_platforms):
        resp = client.post(
            "/posting",
            json={"message": "Grow your business online today with https://example.com"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert len(body["results"]) == 5
        assert body["results"][0]["platform"] == "Mastodon"
        assert body["results"][0]["status"] == "success"
        assert body["results"][0]["posted_url"] == "https://mastodon.social/@demo/1"
