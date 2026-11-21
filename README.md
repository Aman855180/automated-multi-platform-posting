# Automated Multi-Platform Posting System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063.svg)](https://docs.pydantic.dev/)
[![Tests](https://img.shields.io/badge/Tests-42%20Passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

A high-performance, asynchronous multi-platform publishing engine built with **FastAPI**, **Pydantic v2**, and **HTTPX**. The application exposes a single REST API endpoint (`POST /posting`) that accepts a short update message containing a Call-To-Action (CTA) link and automatically broadcasts it concurrently across five major third-party platforms via their official APIs.

---

## Table of Contents

- [1. Project Objectives](#1-project-objectives)
- [2. Technology Stack](#2-technology-stack)
- [3. Architecture & Execution Workflow](#3-architecture--execution-workflow)
- [4. Five Supported Platform Integrations](#4-five-supported-platform-integrations)
- [5. Input Validation Rules](#5-input-validation-rules)
- [6. Project Structure](#6-project-structure)
- [7. Installation & Quickstart](#7-installation--quickstart)
- [8. Environment Configuration](#8-environment-configuration)
- [9. Running the Server on Port 4000](#9-running-the-server-on-port-4000)
- [10. API Specification & Sample Payloads](#10-api-specification--sample-payloads)
  - [Endpoint Details](#endpoint-details)
  - [Sample 1: Complete Success Response](#sample-1-complete-success-response)
  - [Sample 2: Partial Failure Response](#sample-2-partial-failure-response)
  - [Sample 3: Validation Error Response (HTTP 422)](#sample-3-validation-error-response-http-422)
- [11. Concurrency & Fault Isolation](#11-concurrency--fault-isolation)
- [12. Automated Testing Suite](#12-automated-testing-suite)
- [13. Live Publishing Verification Evidence](#13-live-publishing-verification-evidence)
- [14. Security & Credential Handling](#14-security--credential-handling)
- [15. License](#15-license)

---

## 1. Project Objectives

The system is developed in accordance with the *Python Practical Test – Automated Multi-Platform Posting System* specification:

1. **Centralized Ingestion**: Expose `POST http://localhost:4000/posting` taking `{ "message": "..." }`.
2. **Strict Validation**: Enforce a 200-character ceiling, reject empty/whitespace payloads, and mandate exactly one valid HTTP/HTTPS CTA URL.
3. **Internal Platform Selection**: The client does not specify or choose platforms; the backend manages target platforms internally.
4. **Concurrent Multi-Platform Publishing**: Automatically broadcast the validated message across five distinct platforms via their official APIs using asynchronous tasks.
5. **Fault Isolation**: Every platform operates within an independent exception and timeout boundary. Failure on one platform must never interrupt or cancel remaining platforms.
6. **Standardized Response Reporting**: Return a consolidated JSON payload capturing each platform's name, execution status, canonical URL, public access flag, UTC timestamp, and specific error diagnostics.

---

## 2. Technology Stack

| Component | Technology | Rationale |
|---|---|---|
| **Language** | Python 3.10 – 3.13 | Native asynchronous runtime with `asyncio` |
| **Framework** | FastAPI (v0.115+) | Modern, high-throughput ASGI framework with automatic OpenAPI documentation |
| **ASGI Server** | Uvicorn (v0.30+) | Production ASGI server with async event loop support |
| **Validation** | Pydantic v2 (v2.8+) | Strict compiled data modeling and custom regex domain validators |
| **HTTP Client** | HTTPX (v0.27+) | Async HTTP/1.1 and HTTP/2 client with connection pooling and timeouts |
| **Configuration** | Pydantic Settings | Type-safe environment variable parsing from `.env` |
| **Testing** | Pytest & pytest-asyncio | Deterministic async unit and integration testing suite |

---

## 3. Architecture & Execution Workflow

```
                        ┌────────────────────────────┐
                        │    Client (HTTP Request)   │
                        └─────────────┬──────────────┘
                                      │ POST http://localhost:4000/posting
                                      ▼
                        ┌────────────────────────────┐
                        │   FastAPI Endpoint Layer   │
                        └─────────────┬──────────────┘
                                      │
                          [Pydantic v2 Validator]
                          - Length <= 200 chars
                          - Exactly 1 valid CTA URL
                          - Punctuation & host checks
                                      │
                                      ▼
                        ┌────────────────────────────┐
                        │       PostingService       │
                        │  (Internal Orchestration)  │
                        └─────────────┬──────────────┘
                                      │
                 ┌────────────────────┼────────────────────┐
                 │    asyncio.gather(*tasks, return_exceptions=True)
                 ▼                    ▼                    ▼
          ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
          │  Telegram   │      │   Bluesky   │      │  Mastodon   │ ... [Discord, Dev.to]
          │   Bot API   │      │ AT Protocol │      │ Statuses API│
          └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
                 │                    │                    │
                 └────────────────────┼────────────────────┘
                                      │ Consolidated PlatformResult[]
                                      ▼
                        ┌────────────────────────────┐
                        │    Consolidated JSON       │
                        │  (success + results list)  │
                        └────────────────────────────┘
```

---

## 4. Five Supported Platform Integrations

The system integrates directly with five platforms via their official APIs:

| Platform | Official API Documentation | Authentication Mechanism | Method & Endpoint |
|---|---|---|---|
| **1. Telegram** | [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage) | Bot Token | `POST https://api.telegram.org/bot<token>/sendMessage` |
| **2. Bluesky** | [AT Protocol XRPC API](https://docs.bsky.app/docs/category/at-protocol-api) | App Password & Session JWT | `POST /xrpc/com.atproto.server.createSession`<br>`POST /xrpc/com.atproto.repo.createRecord` |
| **3. Mastodon** | [Mastodon Statuses API](https://docs.joinmastodon.org/methods/statuses/#create) | OAuth2 Bearer Token (`write:statuses`) | `POST <instance>/api/v1/statuses` |
| **4. Discord** | [Discord Webhooks API](https://discord.com/developers/docs/resources/webhook#execute-webhook) | Webhook URL Token | `POST <webhook_url>?wait=true` |
| **5. Dev.to** | [Forem / Dev.to Articles API](https://developers.forem.com/api/v1#tag/articles/operation/createArticle) | API Key (`api-key` header) | `POST https://dev.to/api/articles` |

---

## 5. Input Validation Rules

Incoming requests to `POST /posting` are processed through `PostingRequest` in `app/schemas.py`:

1. **Character Limit**: Message length must not exceed 200 characters (`len(message) <= 200`).
2. **Exactly One CTA URL**: The message must contain exactly one valid HTTP or HTTPS URL. Messages with 0 URLs or 2+ URLs are rejected with HTTP 422.
3. **Punctuation Trimming**: Conversational trailing punctuation (`.`, `!`, `,`, `?`) directly appended to links (e.g. `Visit https://example.com!`) is trimmed safely. Balanced parentheses (e.g. Wikipedia links) are preserved.
4. **Host & Protocol Validation**: URLs must use `http://` or `https://`. Hostnames are verified against domain patterns, `localhost`, and valid IPv4 addresses with optional ports. Unsupported schemes (`ftp://`, `mailto:`, `file://`) trigger explicit validation errors.
5. **No Empty Payloads**: Empty strings or whitespace-only messages are rejected immediately.

---

## 6. Project Structure

```text
automated-posting/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI application and route endpoints
│   ├── schemas.py               # Pydantic request, result, and response schemas
│   ├── config.py                # Environment configuration settings
│   │
│   ├── platforms/
│   │   ├── __init__.py          # Platform registry
│   │   ├── base.py              # BasePlatform abstract contract
│   │   ├── telegram.py          # Telegram Bot API integration
│   │   ├── bluesky.py           # Bluesky AT Protocol XRPC integration
│   │   ├── mastodon.py          # Mastodon Statuses API integration
│   │   ├── discord.py           # Discord Webhook API integration
│   │   └── devto.py             # Dev.to Forem REST API integration
│   │
│   └── services/
│       ├── __init__.py
│       └── posting_service.py   # Asynchronous multi-platform coordinator
│
├── tests/
│   ├── __init__.py
│   ├── test_validation.py       # Pydantic URL and boundary unit tests (15 tests)
│   ├── test_platforms.py        # Isolated platform tests with mocked HTTP (19 tests)
│   └── test_posting.py          # Concurrency, timeout, and API endpoint tests (8 tests)
│
├── scripts/
│   ├── live_audit.py            # Local server integration audit runner
│   ├── publish_live.py          # Real-world 5-platform live publishing runner
│   ├── verify_telegram_auth.py  # Read-only Telegram credential verification
│   ├── verify_bluesky_auth.py   # Read-only Bluesky credential verification
│   ├── verify_mastodon_auth.py  # Read-only Mastodon credential verification
│   ├── verify_discord_auth.py   # Read-only Discord webhook verification
│   └── verify_devto_auth.py     # Read-only Dev.to API key verification
│
├── .env.example                 # Clean environment variable template
├── .gitignore                   # Protection rules (excludes .env and credentials)
├── pytest.ini                   # Pytest async test runner configuration
├── requirements.txt             # Locked project dependencies
└── README.md                    # System documentation
```

---

## 7. Installation & Quickstart

### Prerequisites

- Python 3.10+ (tested on Python 3.13.1)
- Git

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Aman855180/automated-multi-platform-posting.git
   cd automated-multi-platform-posting
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 8. Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Populate `.env` with your platform credentials:

```env
# Server Configuration
APP_HOST=0.0.0.0
APP_PORT=4000
APP_ENV=development
REQUEST_TIMEOUT_SECONDS=10.0

# 1. Mastodon API
MASTODON_INSTANCE_URL=https://mastodon.social
MASTODON_ACCESS_TOKEN=your_mastodon_access_token

# 2. Bluesky (AT Protocol)
BLUESKY_HANDLE=your_handle.bsky.social
BLUESKY_APP_PASSWORD=your_app_password
BLUESKY_SERVICE_URL=https://bsky.social

# 3. Telegram Bot API
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=@your_public_channel
TELEGRAM_CHANNEL_USERNAME=your_public_channel

# 4. Discord Webhook API
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook/url
DISCORD_SERVER_ID=your_server_guild_id

# 5. Dev.to API Key
DEVTO_API_KEY=your_devto_api_key
```

*(Any platform left unconfigured fails gracefully with clear error diagnostics without breaking other platforms).*

---

## 9. Running the Server on Port 4000

Start the FastAPI application with Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

The application will bind to:
- **API Base:** `http://localhost:4000`
- **Interactive Swagger Documentation:** `http://localhost:4000/docs`
- **ReDoc Documentation:** `http://localhost:4000/redoc`
- **Health Check Endpoint:** `http://localhost:4000/health`

---

## 10. API Specification & Sample Payloads

### Endpoint Details

- **Route:** `POST /posting`
- **Content-Type:** `application/json`
- **Request Body:**
  ```json
  {
    "message": "Check out our latest business platform and grow your online visibility. https://example.com"
  }
  ```

---

### Sample 1: Complete Success Response

When all five platforms successfully publish the message:

```json
{
  "success": true,
  "results": [
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@ak123_/117653877699840238",
      "public_access": true,
      "date": "2026-11-21",
      "time": "10:08:22",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/ak1223-04.bsky.social/post/3n2su7bomav2m",
      "public_access": true,
      "date": "2026-11-21",
      "time": "10:08:19",
      "error": null
    },
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/my_test_broadcast_123/8",
      "public_access": true,
      "date": "2026-11-21",
      "time": "10:08:22",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "success",
      "posted_url": "https://discord.com/channels/1573623713344000062/1573623714824855605/1573641214257791028",
      "public_access": true,
      "date": "2026-11-21",
      "time": "10:08:22",
      "error": null
    },
    {
      "platform": "Dev.to",
      "status": "success",
      "posted_url": "https://dev.to/aman_kumar_34c0fcd32e19fc/manual-verification-test-for-automated-multi-platform-pos-18e7",
      "public_access": true,
      "date": "2026-11-21",
      "time": "10:08:22",
      "error": null
    }
  ]
}
```

---

### Sample 2: Partial Failure Response

If one platform encounters an issue (e.g. rate limit, bad auth), other platforms succeed unimpeded, and overall `success` reflects `false`:

```json
{
  "success": false,
  "results": [
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@ak123_/117653877699840238",
      "public_access": true,
      "date": "2026-11-21",
      "time": "10:08:22",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Authentication failed: Invalid Bluesky handle or app password."
    },
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/my_test_broadcast_123/8",
      "public_access": true,
      "date": "2026-11-21",
      "time": "10:08:22",
      "error": null
    },
    {
      "platform": "Discord",
      "status": "success",
      "posted_url": "https://discord.com/channels/1573623713344000062/1573623714824855605/1573641214257791028",
      "public_access": true,
      "date": "2026-11-21",
      "time": "10:08:22",
      "error": null
    },
    {
      "platform": "Dev.to",
      "status": "success",
      "posted_url": "https://dev.to/aman_kumar_34c0fcd32e19fc/manual-verification-test-for-automated-multi-platform-pos-18e7",
      "public_access": true,
      "date": "2026-11-21",
      "time": "10:08:22",
      "error": null
    }
  ]
}
```

---

### Sample 3: Validation Error Response (HTTP 422)

Request with multiple URLs or exceeding 200 characters:

```json
{
  "message": "Visit our platform at https://example.com and check docs at https://docs.example.com"
}
```

Response (`HTTP 422 Unprocessable Entity`):
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "message"],
      "msg": "Value error, Message must contain exactly one CTA link, but found 2: https://example.com, https://docs.example.com",
      "input": "Visit our platform at https://example.com and check docs at https://docs.example.com"
    }
  ]
}
```

---

## 11. Concurrency & Fault Isolation

The core orchestration in `app/services/posting_service.py` ensures robust production behavior:

1. **Non-blocking Concurrency**: All platforms are invoked simultaneously using `asyncio.gather(*tasks, return_exceptions=True)`. Total wall-clock time is bounded by the slowest individual platform rather than the sum of all platform latencies.
2. **Per-Platform Timeout Envelope**: Each platform execution is guarded by `asyncio.wait_for(task, timeout=REQUEST_TIMEOUT_SECONDS + 0.5)`. A hanging platform will be terminated without blocking the remaining integrations.
3. **Exception Shielding**: Handled and unhandled exceptions are caught and transformed into clean `PlatformResult(status="failed", error=...)` records, ensuring the FastAPI HTTP endpoint always returns a valid HTTP 200 response with consolidated diagnostic details.

---

## 12. Automated Testing Suite

The project includes **42 automated unit and integration tests** built with `pytest` and `pytest-asyncio`.

### Run All Tests

```bash
pytest -v
```

### Latest Test Results

```text
============================= test session starts =============================
platform win32 -- Python 3.13.1, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\dubey\.gemini\antigravity\scratch\automated-posting
configfile: pytest.ini
plugins: anyio-4.16.0, asyncio-1.5.0
collected 42 items

tests/test_platforms.py::test_mastodon_missing_credentials PASSED        [  2%]
tests/test_platforms.py::test_mastodon_publish_success PASSED            [  4%]
tests/test_platforms.py::test_mastodon_auth_failure PASSED               [  7%]
tests/test_platforms.py::test_mastodon_permission_denied PASSED          [  9%]
tests/test_platforms.py::test_mastodon_rate_limit PASSED                 [ 11%]
tests/test_platforms.py::test_mastodon_timeout PASSED                    [ 14%]
tests/test_platforms.py::test_bluesky_missing_credentials PASSED         [ 16%]
tests/test_platforms.py::test_bluesky_publish_success PASSED             [ 19%]
tests/test_platforms.py::test_bluesky_auth_failure_401 PASSED            [ 21%]
tests/test_platforms.py::test_bluesky_auth_failure_400_authentication_required PASSED [ 23%]
tests/test_platforms.py::test_bluesky_rate_limit PASSED                  [ 26%]
tests/test_platforms.py::test_telegram_missing_credentials PASSED        [ 28%]
tests/test_platforms.py::test_telegram_publish_success_public_channel PASSED [ 30%]
tests/test_platforms.py::test_telegram_publish_success_private_chat PASSED [ 33%]
tests/test_platforms.py::test_telegram_token_not_found_404 PASSED        [ 35%]
tests/test_discord_missing_credentials PASSED                             [ 38%]
tests/test_discord_publish_success PASSED                                 [ 40%]
tests/test_devto_missing_credentials PASSED                               [ 42%]
tests/test_devto_publish_success PASSED                                   [ 45%]
tests/test_posting.py::test_health_check_endpoint PASSED                 [ 47%]
tests/test_posting.py::test_posting_endpoint_validation_errors PASSED    [ 50%]
tests/test_posting.py::test_posting_service_all_success PASSED           [ 52%]
tests/test_posting.py::test_posting_service_partial_failure PASSED       [ 54%]
tests/test_posting.py::test_posting_service_all_failure PASSED           [ 57%]
tests/test_posting.py::test_platform_timeout_resilience PASSED           [ 59%]
tests/test_posting.py::test_unhandled_exception_isolation PASSED         [ 61%]
tests/test_posting.py::test_endpoint_end_to_end_with_injected_service PASSED [ 64%]
tests/test_validation.py::test_valid_message_with_single_url PASSED      [ 66%]
tests/test_validation.py::test_valid_message_with_trailing_punctuation PASSED [ 69%]
tests/test_validation.py::test_valid_message_with_query_params_and_fragment PASSED [ 71%]
tests/test_validation.py::test_valid_message_with_port PASSED            [ 73%]
tests/test_validation.py::test_valid_message_with_ipv4 PASSED            [ 76%]
tests/test_validation.py::test_valid_message_enclosed_in_parentheses PASSED [ 78%]
tests/test_validation.py::test_valid_message_with_balanced_url_parentheses PASSED [ 80%]
tests/test_validation.py::test_empty_message_rejected PASSED             [ 83%]
tests/test_validation.py::test_whitespace_only_message_rejected PASSED   [ 85%]
tests/test_validation.py::test_message_exceeding_200_chars_rejected PASSED [ 88%]
tests/test_validation.py::test_message_exactly_200_chars_accepted PASSED [ 90%]
tests/test_validation.py::test_message_without_url_rejected PASSED       [ 92%]
tests/test_validation.py::test_message_with_multiple_urls_rejected PASSED [ 95%]
tests/test_validation.py::test_unsupported_scheme_rejected PASSED        [ 97%]
tests/test_validation.py::test_malformed_url_rejected PASSED             [100%]

======================= 42 passed, 1 warning in 12.51s ========================
```

---

## 13. Live Publishing Verification Evidence

Real live broadcasts were executed and verified across all five platforms:

| Platform | Official API Used | Verified Live Post Link | Public Access Status |
| :--- | :--- | :--- | :--- |
| **Telegram** | Bot API (`POST /sendMessage`) | [https://t.me/my_test_broadcast_123/8](https://t.me/my_test_broadcast_123/8) | **Fully Public**: Viewable directly on the web without logging in. |
| **Bluesky** | AT Protocol (`POST createRecord`) | [https://bsky.app/profile/ak1223-04.bsky.social/post/3n2su7bomav2m](https://bsky.app/profile/ak1223-04.bsky.social/post/3n2su7bomav2m) | **Fully Public**: Canonical permalink visible worldwide. |
| **Mastodon** | Statuses API (`POST /api/v1/statuses`) | [https://mastodon.social/@ak123_/117653877699840238](https://mastodon.social/@ak123_/117653877699840238) | **Fully Public**: Federated toot accessible via any browser. |
| **Discord** | Webhooks API (`POST ?wait=true`) | [https://discord.com/channels/1573623713344000062/1573623714824855605/1573641214257791028](https://discord.com/channels/1573623713344000062/1573623714824855605/1573641214257791028) | **Server-Restricted**: Link is valid, but Discord requires guild/server membership to render the message in-app. |
| **Dev.to** | Forem Articles API (`POST /api/articles`) | [https://dev.to/aman_kumar_34c0fcd32e19fc/manual-verification-test-for-automated-multi-platform-pos-18e7](https://dev.to/aman_kumar_34c0fcd32e19fc/manual-verification-test-for-automated-multi-platform-pos-18e7) | **Fully Public**: Published article live on developer portal. |

---

## 14. Security & Credential Handling

- **No Secrets in Version Control**: `.env` is excluded in `.gitignore` and has never been committed.
- **Template Provided**: `.env.example` provides documentation and blank placeholders without leaking tokens.
- **Dynamic Loading**: Secrets are managed securely through Pydantic Settings and loaded directly into memory at runtime.
- **Safe Error Reporting**: Exception handlers sanitize internal error messages to ensure authorization headers, API keys, and webhook secrets are never returned in client HTTP responses.

---

## 15. License

This project is licensed under the MIT License.
