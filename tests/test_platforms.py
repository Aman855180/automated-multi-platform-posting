"""Unit tests for individual platform integrations with mocked HTTP responses."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
import httpx
import pytest

from app.config import Settings
from app.platforms.bluesky import BlueskyPlatform
from app.platforms.linkedin import LinkedInPlatform
from app.platforms.mastodon import MastodonPlatform
from app.platforms.reddit import RedditPlatform
from app.platforms.telegram import TelegramPlatform
from app.platforms.wordpress import WordPressPlatform
from app.platforms.discord import DiscordPlatform
from app.platforms.devto import DevToPlatform


# ==============================================================================
# Mastodon Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_mastodon_missing_credentials():
    """Ensure Mastodon fails gracefully when credentials are not configured."""
    config = Settings(MASTODON_ACCESS_TOKEN=None)
    platform = MastodonPlatform(config=config)
    result = await platform.publish("Test message https://example.com")

    assert result.platform == "Mastodon"
    assert result.status == "failed"
    assert "Missing credentials" in (result.error or "")
    assert result.posted_url is None


@pytest.mark.asyncio
async def test_mastodon_publish_success():
    """Ensure Mastodon handles successful status publication."""
    config = Settings(
        MASTODON_INSTANCE_URL="https://mastodon.social",
        MASTODON_ACCESS_TOKEN="fake_token_123",
    )
    platform = MastodonPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "id": "11223344",
            "url": "https://mastodon.social/@tester/11223344",
            "uri": "https://mastodon.social/users/tester/statuses/11223344",
            "created_at": "2026-11-20T12:30:00.000Z",
            "visibility": "public",
        },
        request=httpx.Request("POST", "https://mastodon.social/api/v1/statuses"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check this https://example.com")

        assert result.status == "success"
        assert result.posted_url == "https://mastodon.social/@tester/11223344"
        assert result.public_access is True
        assert result.date == "2026-11-20"
        assert result.time == "12:30:00"
        assert result.error is None


@pytest.mark.asyncio
async def test_mastodon_auth_failure():
    """Ensure Mastodon returns a clear error on 401 Unauthorized."""
    config = Settings(
        MASTODON_INSTANCE_URL="https://mastodon.social",
        MASTODON_ACCESS_TOKEN="invalid_token",
    )
    platform = MastodonPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=401,
        text="The access token is invalid",
        request=httpx.Request("POST", "https://mastodon.social/api/v1/statuses"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check this https://example.com")

        assert result.status == "failed"
        assert "Authentication failed" in (result.error or "")
        assert result.posted_url is None


@pytest.mark.asyncio
async def test_mastodon_permission_denied():
    """Ensure Mastodon returns a clear error on 403 Forbidden."""
    config = Settings(
        MASTODON_INSTANCE_URL="https://mastodon.social",
        MASTODON_ACCESS_TOKEN="read_only_token",
    )
    platform = MastodonPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=403,
        json={"error": "This action is outside the authorized scopes"},
        request=httpx.Request("POST", "https://mastodon.social/api/v1/statuses"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check this https://example.com")

        assert result.status == "failed"
        assert "Permission denied" in (result.error or "")


@pytest.mark.asyncio
async def test_mastodon_rate_limit():
    """Ensure Mastodon returns rate limit error on 429."""
    config = Settings(
        MASTODON_INSTANCE_URL="https://mastodon.social",
        MASTODON_ACCESS_TOKEN="token_123",
    )
    platform = MastodonPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=429,
        text="Throttled",
        request=httpx.Request("POST", "https://mastodon.social/api/v1/statuses"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check this https://example.com")

        assert result.status == "failed"
        assert "Rate limit exceeded" in (result.error or "")


@pytest.mark.asyncio
async def test_mastodon_timeout():
    """Ensure Mastodon returns failure result when request times out."""
    config = Settings(
        MASTODON_INSTANCE_URL="https://mastodon.social",
        MASTODON_ACCESS_TOKEN="test_token",
    )
    platform = MastodonPlatform(config=config)

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.TimeoutException("Connection timed out")
        result = await platform.publish("Check this https://example.com")

        assert result.status == "failed"
        assert "timed out" in (result.error or "")


# ==============================================================================
# Bluesky Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_bluesky_missing_credentials():
    """Ensure Bluesky fails gracefully when handle or password are missing."""
    config = Settings(BLUESKY_HANDLE=None, BLUESKY_APP_PASSWORD=None)
    platform = BlueskyPlatform(config=config)
    result = await platform.publish("Test message https://example.com")

    assert result.status == "failed"
    assert "Missing credentials" in (result.error or "")


@pytest.mark.asyncio
async def test_bluesky_publish_success():
    """Ensure Bluesky session creation and post record creation succeed."""
    config = Settings(
        BLUESKY_HANDLE="user.bsky.social",
        BLUESKY_APP_PASSWORD="secret_app_password",
        BLUESKY_SERVICE_URL="https://bsky.social",
    )
    platform = BlueskyPlatform(config=config)

    session_resp = httpx.Response(
        status_code=200,
        json={
            "accessJwt": "jwt_token_abc",
            "did": "did:plc:test12345",
            "handle": "user.bsky.social",
        },
        request=httpx.Request("POST", "https://bsky.social/xrpc/com.atproto.server.createSession"),
    )

    record_resp = httpx.Response(
        status_code=200,
        json={
            "uri": "at://did:plc:test12345/app.bsky.feed.post/3kbxyz123",
            "cid": "bafyreih5xyz",
        },
        request=httpx.Request("POST", "https://bsky.social/xrpc/com.atproto.repo.createRecord"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [session_resp, record_resp]
        result = await platform.publish("Visit https://example.com")

        assert result.status == "success"
        assert result.posted_url == "https://bsky.app/profile/user.bsky.social/post/3kbxyz123"
        assert result.public_access is True
        assert result.error is None


@pytest.mark.asyncio
async def test_bluesky_auth_failure_401():
    """Ensure Bluesky handles 401 invalid handle or password gracefully."""
    config = Settings(
        BLUESKY_HANDLE="user.bsky.social",
        BLUESKY_APP_PASSWORD="wrong_password",
    )
    platform = BlueskyPlatform(config=config)

    session_resp = httpx.Response(
        status_code=401,
        json={"error": "AuthenticationRequired", "message": "Invalid identifier or password"},
        request=httpx.Request("POST", "https://bsky.social/xrpc/com.atproto.server.createSession"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = session_resp
        result = await platform.publish("Visit https://example.com")

        assert result.status == "failed"
        assert "Authentication failed" in (result.error or "")


@pytest.mark.asyncio
async def test_bluesky_auth_failure_400_authentication_required():
    """Ensure Bluesky handles AT Protocol 400 AuthenticationRequired as auth failure."""
    config = Settings(
        BLUESKY_HANDLE="user.bsky.social",
        BLUESKY_APP_PASSWORD="wrong_password",
    )
    platform = BlueskyPlatform(config=config)

    session_resp = httpx.Response(
        status_code=400,
        json={"error": "AuthenticationRequired", "message": "Invalid identifier or password"},
        request=httpx.Request("POST", "https://bsky.social/xrpc/com.atproto.server.createSession"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = session_resp
        result = await platform.publish("Visit https://example.com")

        assert result.status == "failed"
        assert "Authentication failed" in (result.error or "")


@pytest.mark.asyncio
async def test_bluesky_rate_limit():
    """Ensure Bluesky handles 429 rate limit error."""
    config = Settings(
        BLUESKY_HANDLE="user.bsky.social",
        BLUESKY_APP_PASSWORD="correct_password",
    )
    platform = BlueskyPlatform(config=config)

    session_resp = httpx.Response(
        status_code=200,
        json={"accessJwt": "jwt_123", "did": "did:plc:123", "handle": "user.bsky.social"},
        request=httpx.Request("POST", "https://bsky.social/xrpc/com.atproto.server.createSession"),
    )
    post_resp = httpx.Response(
        status_code=429,
        text="Rate limit exceeded",
        request=httpx.Request("POST", "https://bsky.social/xrpc/com.atproto.repo.createRecord"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [session_resp, post_resp]
        result = await platform.publish("Visit https://example.com")

        assert result.status == "failed"
        assert "Rate limit exceeded" in (result.error or "")


# ==============================================================================
# Telegram Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_telegram_missing_credentials():
    """Ensure Telegram fails gracefully when bot token or chat ID is missing."""
    config = Settings(TELEGRAM_BOT_TOKEN=None, TELEGRAM_CHAT_ID=None)
    platform = TelegramPlatform(config=config)
    result = await platform.publish("Test message https://example.com")

    assert result.status == "failed"
    assert "Missing credentials" in (result.error or "")


@pytest.mark.asyncio
async def test_telegram_publish_success_public_channel():
    """Ensure Telegram formats public URL when channel username is available."""
    config = Settings(
        TELEGRAM_BOT_TOKEN="123456:ABC-DEF",
        TELEGRAM_CHAT_ID="@my_channel",
        TELEGRAM_CHANNEL_USERNAME="my_channel",
    )
    platform = TelegramPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "ok": True,
            "result": {
                "message_id": 987,
                "date": 1763640000,
                "chat": {
                    "id": -1001234567,
                    "title": "My Public Channel",
                    "username": "my_channel",
                    "type": "channel",
                },
                "text": "Check out https://example.com",
            },
        },
        request=httpx.Request("POST", "https://api.telegram.org/bot123456:ABC-DEF/sendMessage"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check out https://example.com")

        assert result.status == "success"
        assert result.posted_url == "https://t.me/my_channel/987"
        assert result.public_access is True
        assert result.error is None


@pytest.mark.asyncio
async def test_telegram_publish_success_private_chat():
    """Ensure Telegram reports public_access=False when chat has no public username."""
    config = Settings(
        TELEGRAM_BOT_TOKEN="123456:ABC-DEF",
        TELEGRAM_CHAT_ID="-100999999",
        TELEGRAM_CHANNEL_USERNAME=None,
    )
    platform = TelegramPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "ok": True,
            "result": {
                "message_id": 55,
                "date": 1763640000,
                "chat": {
                    "id": -100999999,
                    "title": "Private Team Group",
                    "type": "group",
                },
                "text": "Check out https://example.com",
            },
        },
        request=httpx.Request("POST", "https://api.telegram.org/bot123456:ABC-DEF/sendMessage"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check out https://example.com")

        assert result.status == "success"
        assert result.posted_url is None
        assert result.public_access is False


@pytest.mark.asyncio
async def test_telegram_token_not_found_404():
    """Ensure Telegram handles 404 invalid bot token format with actionable error."""
    config = Settings(
        TELEGRAM_BOT_TOKEN="invalid_token",
        TELEGRAM_CHAT_ID="@my_channel",
    )
    platform = TelegramPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=404,
        json={"ok": False, "error_code": 404, "description": "Not Found"},
        request=httpx.Request("POST", "https://api.telegram.org/botinvalid_token/sendMessage"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check out https://example.com")

        assert result.status == "failed"
        assert "HTTP 404" in (result.error or "")


# ==============================================================================
# Reddit Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_reddit_missing_credentials():
    """Ensure Reddit fails gracefully when any OAuth credential is missing."""
    config = Settings(
        REDDIT_CLIENT_ID=None,
        REDDIT_CLIENT_SECRET=None,
        REDDIT_USERNAME=None,
        REDDIT_PASSWORD=None,
    )
    platform = RedditPlatform(config=config)
    result = await platform.publish("Check out https://example.com")

    assert result.status == "failed"
    assert "Missing credentials" in (result.error or "")


@pytest.mark.asyncio
async def test_reddit_publish_success():
    """Ensure Reddit token exchange and submit API work correctly."""
    config = Settings(
        REDDIT_CLIENT_ID="fake_cid",
        REDDIT_CLIENT_SECRET="fake_secret",
        REDDIT_USERNAME="test_bot",
        REDDIT_PASSWORD="test_password",
        REDDIT_SUBREDDIT="test",
    )
    platform = RedditPlatform(config=config)

    token_resp = httpx.Response(
        status_code=200,
        json={"access_token": "reddit_bearer_token_xyz", "token_type": "bearer"},
        request=httpx.Request("POST", "https://www.reddit.com/api/v1/access_token"),
    )

    submit_resp = httpx.Response(
        status_code=200,
        json={
            "json": {
                "errors": [],
                "data": {
                    "url": "https://www.reddit.com/r/test/comments/123abc/check_out_our_platform/",
                    "id": "t3_123abc",
                    "name": "t3_123abc",
                },
            }
        },
        request=httpx.Request("POST", "https://oauth.reddit.com/api/submit"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = [token_resp, submit_resp]
        result = await platform.publish("Check out our platform https://example.com")

        assert result.status == "success"
        assert result.posted_url == "https://www.reddit.com/r/test/comments/123abc/check_out_our_platform/"
        assert result.public_access is True
        assert result.error is None


@pytest.mark.asyncio
async def test_reddit_forbidden_403():
    """Ensure Reddit handles 403 user agent block or forbidden subreddit."""
    config = Settings(
        REDDIT_CLIENT_ID="fake_cid",
        REDDIT_CLIENT_SECRET="fake_secret",
        REDDIT_USERNAME="test_bot",
        REDDIT_PASSWORD="test_password",
    )
    platform = RedditPlatform(config=config)

    token_resp = httpx.Response(
        status_code=403,
        text="Blocked by Reddit",
        request=httpx.Request("POST", "https://www.reddit.com/api/v1/access_token"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = token_resp
        result = await platform.publish("Check out https://example.com")

        assert result.status == "failed"
        assert "Access forbidden" in (result.error or "")


# ==============================================================================
# LinkedIn Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_linkedin_missing_credentials():
    """Ensure LinkedIn fails gracefully when access token or author URN is missing."""
    config = Settings(LINKEDIN_ACCESS_TOKEN=None, LINKEDIN_AUTHOR_URN=None)
    platform = LinkedInPlatform(config=config)
    result = await platform.publish("Check out https://example.com")

    assert result.status == "failed"
    assert "Missing credentials" in (result.error or "")


@pytest.mark.asyncio
async def test_linkedin_publish_success():
    """Ensure LinkedIn returns post URL constructed from returned URN."""
    config = Settings(
        LINKEDIN_ACCESS_TOKEN="li_access_token_123",
        LINKEDIN_AUTHOR_URN="urn:li:person:abcdef",
    )
    platform = LinkedInPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=201,
        headers={"x-restli-id": "urn:li:share:7123456789012345678"},
        request=httpx.Request("POST", "https://api.linkedin.com/rest/posts"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check out https://example.com")

        assert result.status == "success"
        assert result.posted_url == "https://www.linkedin.com/feed/update/urn:li:share:7123456789012345678"
        assert result.public_access is True
        assert result.error is None


@pytest.mark.asyncio
async def test_linkedin_forbidden_scope():
    """Ensure LinkedIn handles 403 lack of scope with clear error."""
    config = Settings(
        LINKEDIN_ACCESS_TOKEN="token_lacking_scope",
        LINKEDIN_AUTHOR_URN="urn:li:person:abcdef",
    )
    platform = LinkedInPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=403,
        text="ACCESS_DENIED: w_member_social scope required",
        request=httpx.Request("POST", "https://api.linkedin.com/rest/posts"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check out https://example.com")

        assert result.status == "failed"
        assert "Permission denied" in (result.error or "")


@pytest.mark.asyncio
async def test_linkedin_bad_request_400():
    """Ensure LinkedIn extracts message from 400 Bad Request error."""
    config = Settings(
        LINKEDIN_ACCESS_TOKEN="valid_token",
        LINKEDIN_AUTHOR_URN="urn:li:person:abcdef",
    )
    platform = LinkedInPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=400,
        json={"message": "Author URN is invalid or malformed"},
        request=httpx.Request("POST", "https://api.linkedin.com/rest/posts"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check out https://example.com")

        assert result.status == "failed"
        assert "Author URN is invalid" in (result.error or "")


# ==============================================================================
# WordPress Tests (Extensible 6th Platform)
# ==============================================================================


@pytest.mark.asyncio
async def test_wordpress_publish_success():
    """Ensure WordPress REST API returns public link."""
    config = Settings(
        WORDPRESS_SITE_URL="https://myblog.example.com",
        WORDPRESS_USERNAME="admin",
        WORDPRESS_APP_PASSWORD="abcd efgh ijkl mnop",
    )
    platform = WordPressPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=201,
        json={
            "id": 101,
            "link": "https://myblog.example.com/2026/11/check-out-our-platform/",
            "date_gmt": "2026-11-20T14:00:00",
            "status": "publish",
        },
        request=httpx.Request("POST", "https://myblog.example.com/wp-json/wp/v2/posts"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check out our platform https://example.com")

        assert result.status == "success"
        assert result.posted_url == "https://myblog.example.com/2026/11/check-out-our-platform/"
        assert result.public_access is True
        assert result.date == "2026-11-20"
        assert result.time == "14:00:00"


@pytest.mark.asyncio
async def test_wordpress_missing_credentials():
    """Ensure WordPress reports missing credentials error."""
    config = Settings(WORDPRESS_SITE_URL=None)
    platform = WordPressPlatform(config=config)
    result = await platform.publish("Check out https://example.com")

    assert result.status == "failed"
    assert "Missing credentials" in (result.error or "")


# ==============================================================================
# Discord Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_discord_missing_credentials():
    """Ensure Discord fails gracefully when webhook URL is missing."""
    config = Settings(DISCORD_WEBHOOK_URL=None)
    platform = DiscordPlatform(config=config)
    result = await platform.publish("Check out https://example.com")

    assert result.status == "failed"
    assert "Missing credentials" in (result.error or "")


@pytest.mark.asyncio
async def test_discord_publish_success():
    """Ensure Discord executes webhook with wait=true and constructs channel permalink."""
    config = Settings(
        DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/123/abc",
        DISCORD_SERVER_ID="999888",
    )
    platform = DiscordPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "id": "111222333",
            "channel_id": "444555",
            "timestamp": "2026-11-21T10:00:00.000000+00:00",
        },
        request=httpx.Request("POST", "https://discord.com/api/webhooks/123/abc?wait=true"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check out https://example.com")

        assert result.status == "success"
        assert result.posted_url == "https://discord.com/channels/999888/444555/111222333"
        assert result.public_access is True
        assert result.date == "2026-11-21"
        assert result.time == "10:00:00"


# ==============================================================================
# Dev.to Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_devto_missing_credentials():
    """Ensure Dev.to fails gracefully when API key is missing."""
    config = Settings(DEVTO_API_KEY=None)
    platform = DevToPlatform(config=config)
    result = await platform.publish("Check out https://example.com")

    assert result.status == "failed"
    assert "Missing credentials" in (result.error or "")


@pytest.mark.asyncio
async def test_devto_publish_success():
    """Ensure Dev.to creates an article and returns canonical public URL."""
    config = Settings(DEVTO_API_KEY="test_api_key_123")
    platform = DevToPlatform(config=config)

    mock_resp = httpx.Response(
        status_code=201,
        json={
            "id": 98765,
            "url": "https://dev.to/user/automated-update-123",
            "published_at": "2026-11-21T10:30:00Z",
        },
        request=httpx.Request("POST", "https://dev.to/api/articles"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        result = await platform.publish("Check out our tool https://example.com")

        assert result.status == "success"
        assert result.posted_url == "https://dev.to/user/automated-update-123"
        assert result.public_access is True
        assert result.date == "2026-11-21"
        assert result.time == "10:30:00"

