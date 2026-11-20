# Automated Multi-Platform Posting System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063.svg)](https://docs.pydantic.dev/)
[![Tests](https://img.shields.io/badge/Tests-47%20Passed-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)]()

A high-performance, asynchronous multi-platform publishing engine built with **FastAPI**, **Pydantic v2**, and **HTTPX**. The application exposes a single REST API endpoint (`POST /posting`) that accepts a marketing or update message with a Call-To-Action (CTA) link and automatically broadcasts it concurrently across 5+ major third-party platforms via their official APIs.

---

## Table of Contents

- [1. Architecture & Design Principles](#1-architecture--design-principles)
- [2. Technology Stack](#2-technology-stack)
- [3. Selected Platforms & API Justification](#3-selected-platforms--api-justification)
- [4. Input Validation Rules](#4-input-validation-rules)
- [5. Project Structure](#5-project-structure)
- [6. Installation & Quickstart](#6-installation--quickstart)
- [7. Configuration & Environment Variables](#7-configuration--environment-variables)
- [8. Running the Application](#8-running-the-application)
- [9. API Documentation & Sample Payloads](#9-api-documentation--sample-payloads)
  - [Sample Request](#sample-request)
  - [Sample 1: Complete Success Response](#sample-1-complete-success-response)
  - [Sample 2: Partial Success Response](#sample-2-partial-success-response)
  - [Sample 3: Complete Failure / Missing Credentials Response](#sample-3-complete-failure--missing-credentials-response)
  - [Sample 4: Input Validation Error (HTTP 422)](#sample-4-input-validation-error-http-422)
- [10. Running the Test Suite](#10-running-the-test-suite)
- [11. Real APIs vs. Mock Verification](#11-real-apis-vs-mock-verification)
- [12. Platform Credentials & Permissions Guide](#12-platform-credentials--permissions-guide)

---

## 1. Architecture & Design Principles

The service is engineered following production backend design patterns:

```
                      ┌────────────────────────────┐
                      │    Client (HTTP Request)   │
                      └─────────────┬──────────────┘
                                    │ POST /posting
                                    ▼
                      ┌────────────────────────────┐
                      │   FastAPI Endpoint Layer   │
                      └─────────────┬──────────────┘
                                    │
                        [Pydantic v2 Validator]
                        - Length <= 200 chars
                        - Exactly 1 valid CTA URL
                        - Reject malformed / empty
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │       PostingService       │
                      │  (Internal Orchestration)  │
                      └─────────────┬──────────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 │  asyncio.gather  │  (Concurrent)    │
                 ▼                  ▼                  ▼
          ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
          │  Mastodon   │    │   Bluesky   │    │  Telegram   │ ... [Reddit, LinkedIn, WordPress]
          │ Integration │    │ Integration │    │ Integration │
          └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
                 │                  │                  │
                 └──────────────────┼──────────────────┘
                                    │ Consolidated PlatformResult[]
                                    ▼
                      ┌────────────────────────────┐
                      │    Consolidated JSON       │
                      │  (success + results list)  │
                      └────────────────────────────┘
```

### Core Architecture Highlights

1. **Platform Abstraction Layer (`BasePlatform`)**: All platform integrations inherit from an abstract base class enforcing the contract `async def publish(self, message: str) -> PlatformResult`. Adding a new platform requires only creating a new class extending `BasePlatform` without altering API routes.
2. **Concurrent Non-Blocking Execution**: Publishing across platforms is triggered simultaneously using `asyncio.gather(*tasks, return_exceptions=True)`. A slow or unresponsive platform does not delay or block others.
3. **Fault Isolation & Graceful Degradation**: Each platform operates within its own exception boundary and timeout envelope (`REQUEST_TIMEOUT_SECONDS`). If one platform fails (e.g. rate limit, bad auth, network timeout), the remaining platforms execute unimpeded.
4. **Honest Reporting**: Partial successes are never reported as full successes (`success: false` if any configured platform failed, with detailed individual error diagnostics).
5. **Zero Credential Hardcoding**: All secrets and credentials are read via `pydantic-settings` from environment variables or `.env`.

---

## 2. Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Language** | Python 3.10 - 3.13 | High-performance modern asynchronous runtime |
| **Framework** | FastAPI | ASGI web framework with automatic OpenAPI documentation |
| **Server** | Uvicorn | Blazing-fast ASGI server implementation |
| **Validation** | Pydantic v2 | High-speed data parsing and strict domain validation |
| **HTTP Client** | HTTPX | Asynchronous, connection-pooled HTTP client with HTTP/2 support |
| **Configuration** | Pydantic Settings & Dotenv | Type-safe environment management |
| **Testing** | Pytest & Pytest-Asyncio | Automated asynchronous unit and integration test suite |

---

## 3. Selected Platforms & API Justification

Five primary platforms were selected after rigorous evaluation of official API accessibility, write support, authentication feasibility, and public accessibility:

| Platform | Official API Reference | Auth Mechanism | Public Access Verifiable? | Why Selected? |
|---|---|---|---|---|
| **1. Mastodon** | [Mastodon Statuses API](https://docs.joinmastodon.org/methods/statuses/#create) | OAuth2 Bearer Token (`write:statuses` scope) | **Yes**: returns permanent canonical `url` | Standard ActivityPub protocol; decentralized; developer-friendly token issuance; instantly returns public web permalink. |
| **2. Bluesky** | [AT Protocol XRPC API](https://docs.bsky.app/docs/category/at-protocol-api) | App Password (`com.atproto.server.createSession` & `createRecord`) | **Yes**: permalink at `https://bsky.app/profile/{handle}/post/{rkey}` | Fast-growing decentralized network; modern JSON-RPC over HTTP; app-specific passwords eliminate complex OAuth2 redirect flows. |
| **3. Telegram** | [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage) | Bot Token (`sendMessage`) | **Yes**: `https://t.me/{username}/{message_id}` for public channels | Highest reliability and speed; official bot API requires no human session bypass; direct public channel web viewer. |
| **4. Reddit** | [Reddit Submit API](https://www.reddit.com/dev/api#POST_api_submit) | Script App OAuth2 (Password grant) | **Yes**: returns Reddit post permalink | World's largest forum community; official submit endpoint supports self-posts directly to designated subreddits (`r/test`, etc.). |
| **5. LinkedIn** | [LinkedIn Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api) | OAuth 2.0 User Access Token (`w_member_social`) | **Yes**: permalink at `https://www.linkedin.com/feed/update/{urn}` | Essential B2B and professional platform; official Posts API replaces legacy Shares API and returns canonical URN. |
| **Bonus: WordPress** | [WordPress REST API](https://developer.wordpress.org/rest-api/reference/posts/#create-a-post) | Application Passwords (Basic Auth) | **Yes**: returns published post `link` | Ubiquitous CMS platform powering 40%+ of the web; demonstrates headless CMS content distribution. |

---

## 4. Input Validation Rules

The application implements strict Pydantic v2 domain validation on `POST /posting`:

1. **Character Limit**: Message must not exceed 200 characters (`len(message) <= 200`).
2. **Exactly One CTA Link**: Message must contain exactly one valid HTTP/HTTPS URL. Zero URLs or multiple URLs trigger immediate HTTP 422 errors.
3. **Punctuation Trimming**: Conversational trailing punctuation (`.`, `!`, `,`, `?`) attached to links (e.g. `Visit https://example.com!`) is gracefully trimmed without invalidating the URL.
4. **Valid Domain / Host**: URLs must have a valid scheme (`http` or `https`) and an identifiable network host/domain name.
5. **No Empty / Whitespace-only Strings**: Rejected with descriptive error messages.

---

## 5. Project Structure

```text
automated-posting/
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI server and route handlers
│   ├── schemas.py               # Pydantic request, result, and response models
│   ├── config.py                # Environment configuration via Pydantic Settings
│   │
│   ├── platforms/
│   │   ├── __init__.py          # Platform registry
│   │   ├── base.py              # BasePlatform abstract base class contract
│   │   ├── mastodon.py          # Mastodon Statuses API integration
│   │   ├── bluesky.py           # Bluesky AT Protocol XRPC integration
│   │   ├── telegram.py          # Telegram Bot API integration
│   │   ├── reddit.py            # Reddit OAuth2 & Submit API integration
│   │   ├── linkedin.py          # LinkedIn Posts API integration
│   │   └── wordpress.py         # WordPress REST API integration (extensible)
│   │
│   └── services/
│       ├── __init__.py
│       └── posting_service.py   # Asynchronous concurrent publishing coordinator
│
├── tests/
│   ├── __init__.py
│   ├── test_validation.py       # Pydantic URL and character constraint unit tests
│   ├── test_platforms.py        # Independent platform unit tests with mocked HTTP
│   └── test_posting.py          # Concurrency, timeout, and API endpoint integration tests
│
├── .env.example                 # Credential template for all platforms
├── .gitignore                   # Security exclusion rules
├── pytest.ini                   # Pytest async runner configuration
├── requirements.txt             # Locked project dependencies
└── README.md                    # Project documentation
```

---

## 6. Installation & Quickstart

### Prerequisites

- Python 3.10+ (tested on Python 3.13.1)
- Git

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone <YOUR_PUBLIC_GITHUB_REPO_URL>
   cd automated-posting
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 7. Configuration & Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` to configure your platform credentials. If any platform credentials are left blank, **the system will not crash**: that platform will report an informative `failed` status explaining which credential is missing, while all configured platforms publish normally.

```env
# Application Settings
APP_HOST=0.0.0.0
APP_PORT=4000
APP_ENV=development
REQUEST_TIMEOUT_SECONDS=10.0

# 1. Mastodon
MASTODON_INSTANCE_URL=https://mastodon.social
MASTODON_ACCESS_TOKEN=your_mastodon_access_token

# 2. Bluesky
BLUESKY_HANDLE=your_handle.bsky.social
BLUESKY_APP_PASSWORD=your_app_password
BLUESKY_SERVICE_URL=https://bsky.social

# 3. Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_CHAT_ID=@your_channel_or_chat_id
TELEGRAM_CHANNEL_USERNAME=your_channel_without_at

# 4. Reddit
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password
REDDIT_SUBREDDIT=test
REDDIT_USER_AGENT=automated-posting:v1.0.0 (by /u/your_reddit_username)

# 5. LinkedIn
LINKEDIN_ACCESS_TOKEN=your_linkedin_oauth2_access_token
LINKEDIN_AUTHOR_URN=urn:li:person:your_person_id

# 6. WordPress (Optional)
WORDPRESS_SITE_URL=https://your-wordpress-site.com
WORDPRESS_USERNAME=your_username
WORDPRESS_APP_PASSWORD=abcd efgh ijkl mnop
```

---

## 8. Running the Application

Start the local server using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload
```

The server will be available at:
- **API Base URL**: `http://localhost:4000`
- **Interactive Swagger Docs**: `http://localhost:4000/docs`
- **ReDoc Documentation**: `http://localhost:4000/redoc`
- **Health Check Endpoint**: `http://localhost:4000/health`

---

## 9. API Documentation & Sample Payloads

### Endpoint

```http
POST http://localhost:4000/posting
Content-Type: application/json
```

### Sample Request

```json
{
  "message": "Check out our latest business platform and grow your online visibility. https://example.com"
}
```

---

### Sample 1: Complete Success Response

*(When all 5 platforms have valid credentials and succeed)*

```json
{
  "success": true,
  "results": [
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@dxora_marketing/112345678901234567",
      "public_access": true,
      "date": "2026-11-20",
      "time": "12:30:15",
      "error": null
    },
    {
      "platform": "Bluesky",
      "status": "success",
      "posted_url": "https://bsky.app/profile/dxora.bsky.social/post/3kbxyz12345",
      "public_access": true,
      "date": "2026-11-20",
      "time": "12:30:16",
      "error": null
    },
    {
      "platform": "Telegram",
      "status": "success",
      "posted_url": "https://t.me/dxora_announcements/482",
      "public_access": true,
      "date": "2026-11-20",
      "time": "12:30:14",
      "error": null
    },
    {
      "platform": "Reddit",
      "status": "success",
      "posted_url": "https://www.reddit.com/r/test/comments/18bcdef/check_out_our_latest_business_platform/",
      "public_access": true,
      "date": "2026-11-20",
      "time": "12:30:16",
      "error": null
    },
    {
      "platform": "LinkedIn",
      "status": "success",
      "posted_url": "https://www.linkedin.com/feed/update/urn:li:share:7123456789012345678",
      "public_access": true,
      "date": "2026-11-20",
      "time": "12:30:17",
      "error": null
    }
  ]
}
```

---

### Sample 2: Partial Success Response

*(When some platforms succeed while others fail auth or rate limits)*

```json
{
  "success": false,
  "results": [
    {
      "platform": "Mastodon",
      "status": "success",
      "posted_url": "https://mastodon.social/@dxora/112345678901234567",
      "public_access": true,
      "date": "2026-11-20",
      "time": "12:30:15",
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
      "posted_url": "https://t.me/dxora_channel/482",
      "public_access": true,
      "date": "2026-11-20",
      "time": "12:30:14",
      "error": null
    },
    {
      "platform": "Reddit",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Rate limit exceeded on Reddit API."
    },
    {
      "platform": "LinkedIn",
      "status": "success",
      "posted_url": "https://www.linkedin.com/feed/update/urn:li:share:7123456789012345678",
      "public_access": true,
      "date": "2026-11-20",
      "time": "12:30:17",
      "error": null
    }
  ]
}
```

---

### Sample 3: Complete Failure / Missing Credentials Response

*(Out of the box without `.env` credentials)*

```json
{
  "success": false,
  "results": [
    {
      "platform": "Mastodon",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: MASTODON_INSTANCE_URL and MASTODON_ACCESS_TOKEN must be configured."
    },
    {
      "platform": "Bluesky",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: BLUESKY_HANDLE and BLUESKY_APP_PASSWORD must be configured."
    },
    {
      "platform": "Telegram",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be configured."
    },
    {
      "platform": "Reddit",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, and REDDIT_PASSWORD must be configured."
    },
    {
      "platform": "LinkedIn",
      "status": "failed",
      "posted_url": null,
      "public_access": false,
      "date": null,
      "time": null,
      "error": "Missing credentials: LINKEDIN_ACCESS_TOKEN and LINKEDIN_AUTHOR_URN must be configured."
    }
  ]
}
```

---

### Sample 4: Input Validation Error (HTTP 422)

Request with multiple URLs or missing CTA:

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

## 10. Running the Test Suite & Live Server Audit

The automated test suite uses `pytest` with 47 comprehensive unit and integration tests.

### Execute All Tests

```bash
pytest -v
```

### Run Live Server Audit (End-to-End against Uvicorn on Port 4000)

```bash
python scripts/live_audit.py
```

### Test Coverage Highlights

- **`tests/test_validation.py` (15 tests)**:
  - Valid message with single URL
  - Trailing conversational punctuation trimming (`https://example.com!`)
  - Query parameters and fragment identifiers (`?plan=pro&ref=test#overview`)
  - Non-standard port handling (`:8443`)
  - IPv4 address hosts (`http://192.168.1.1:8000`)
  - Parenthesis-wrapped links (`(https://example.com/demo)`)
  - Balanced internal URL parentheses (`FastAPI_(software)`)
  - Empty string and whitespace-only rejection
  - Message exceeding 200 characters rejection
  - Exactly 200 characters boundary test
  - Missing URL rejection
  - Multiple URLs rejection
  - Unsupported schemes rejection (`ftp://`, `mailto:`)
  - Malformed URL rejection
- **`tests/test_platforms.py` (24 tests)**:
  - Mastodon: missing credentials, 200 success, 401 auth failure, 403 scope error, 429 rate limit, timeout
  - Bluesky: missing credentials, session + record success, 401 auth failure, 400 AuthenticationRequired, 429 rate limit
  - Telegram: missing credentials, public channel URL success, private chat `public_access=False` success, 404 token not found
  - Reddit: missing credentials, token exchange + submit success, 403 forbidden
  - LinkedIn: missing credentials, 201 Created with URN header success, 403 permission denied, 400 bad request error extraction
  - WordPress: 201 Created with permalink success, missing credentials
- **`tests/test_posting.py` (8 tests)**:
  - `GET /health` endpoint inspection
  - `POST /posting` validation error rejection (422)
  - Full concurrent posting with all platforms succeeding (`success: true`)
  - Partial failure isolation (`success: false`, unaffected platforms complete)
  - All platforms failing handling
  - Timeout resilience (one slow platform does not hold up fast platforms)
  - Unhandled exception isolation (crashing platform captured safely)
  - Full end-to-end FastAPI endpoint execution

---

## 11. Real APIs vs. Mock Verification

Honest engineering disclosure regarding API execution:

| Platform | Real API Implementation Status | Automated Test Strategy | Live Verification Feasibility |
|---|---|---|---|
| **Mastodon** | **Fully Implemented** | Mocked HTTP via `unittest.mock` | Requires personal instance account & Bearer token (`write:statuses`). |
| **Bluesky** | **Fully Implemented** | Mocked HTTP via `unittest.mock` | Requires free Bluesky account & App Password. |
| **Telegram** | **Fully Implemented** | Mocked HTTP via `unittest.mock` | Requires Telegram Bot Token (instant via `@BotFather`) and public channel. |
| **Reddit** | **Fully Implemented** | Mocked HTTP via `unittest.mock` | Requires Reddit Developer Script App & account credentials. |
| **LinkedIn** | **Fully Implemented** | Mocked HTTP via `unittest.mock` | Requires LinkedIn Developer App with `w_member_social` permission approval. |
| **WordPress** | **Fully Implemented** | Mocked HTTP via `unittest.mock` | Requires WordPress install with Application Password support. |

> **Note**: Automated tests intentionally mock external HTTP calls (`unittest.mock.patch.object(httpx.AsyncClient, "post")`). This guarantees tests run deterministically in CI/CD without hitting rate limits, leaking credentials, or spamming live feeds.

---

## 12. Platform Credentials & Permissions Guide

Follow these steps to obtain credentials for live broadcasting:

### 1. Mastodon
1. Create an account on any Mastodon instance (e.g. `mastodon.social`).
2. Go to **Preferences -> Development -> New Application**.
3. Grant `write:statuses` scope.
4. Copy the generated **Access Token**.

### 2. Bluesky
1. Sign up at [bsky.app](https://bsky.app).
2. Go to **Settings -> Privacy and Security -> App Passwords**.
3. Generate a new App Password (e.g. `abcd-efgh-ijkl-mnop`).
4. Set `BLUESKY_HANDLE` to your handle and `BLUESKY_APP_PASSWORD` to this token.

### 3. Telegram
1. Open Telegram and search for `@BotFather`.
2. Send `/newbot` and follow the prompts to obtain your **Bot Token**.
3. Create a public channel, add your bot as an **Administrator** with "Post Messages" permission.
4. Set `TELEGRAM_BOT_TOKEN` to your token and `TELEGRAM_CHAT_ID` to `@your_channel`.

### 4. Reddit
1. Navigate to [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps).
2. Click **Create Another App...**, select **script**.
3. Note the **Client ID** (string beneath app name) and **Client Secret**.
4. Configure your Reddit username, password, and target subreddit (e.g. `test`).

### 5. LinkedIn
1. Go to the [LinkedIn Developer Portal](https://www.linkedin.com/developers/).
2. Create an App and associate it with a verified LinkedIn Page.
3. Request the **Share on LinkedIn** and **Sign In with LinkedIn using OpenID Connect** products.
4. Generate an OAuth2 access token with `w_member_social` scope.
5. Provide your Member or Organization URN (format: `urn:li:person:<id>`).

---

## License

This project is licensed under the MIT License.
