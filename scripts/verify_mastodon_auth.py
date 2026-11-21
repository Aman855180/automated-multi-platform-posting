"""Safe verification script for Mastodon Authentication.

Does NOT publish any post. Only tests:
`GET /api/v1/accounts/verify_credentials` - Confirms the access token is valid and returns the account info.
"""

import os
import sys

# Ensure root project directory is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import httpx
from app.config import Settings


def verify_mastodon():
    config = Settings()
    instance_url = (config.MASTODON_INSTANCE_URL or "https://mastodon.social").rstrip("/")
    access_token = config.MASTODON_ACCESS_TOKEN

    print("=" * 65)
    print("MASTODON SAFE AUTHENTICATION TEST")
    print("=" * 65)

    if not access_token or not access_token.strip():
        print("\n[ERROR] MASTODON_ACCESS_TOKEN is missing or blank in .env.")
        print("Please open .env and set: MASTODON_ACCESS_TOKEN=your_token_here")
        return False

    masked_token = access_token[:6] + "..." + access_token[-4:] if len(access_token) > 10 else "***"
    print(f"\n1. Loaded configuration:")
    print(f"   Instance URL: {instance_url}")
    print(f"   Access Token: {masked_token}")

    # Check: Verify Credentials via /api/v1/accounts/verify_credentials
    print("\n2. Contacting Mastodon API: verify_credentials...")
    endpoint = f"{instance_url}/api/v1/accounts/verify_credentials"
    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "User-Agent": "AutomatedMultiPlatformPosting/1.0",
    }

    try:
        resp = httpx.get(endpoint, headers=headers, timeout=10.0)
        data = {}
        try:
            data = resp.json()
        except Exception:
            pass

        if resp.status_code == 200:
            username = data.get("username")
            display_name = data.get("display_name") or username
            profile_url = data.get("url")

            print(f"   [SUCCESS] Access token is valid!")
            print(f"   Account Name:     {display_name}")
            print(f"   Account Handle:   @{username}")
            print(f"   Profile URL:      {profile_url}")

            print("\n" + "=" * 65)
            print("ALL MASTODON AUTHENTICATION CHECKS PASSED!")
            print("Your Mastodon account is authorized and ready for live posting.")
            print("=" * 65)
            return True

        elif resp.status_code == 401:
            print("   [FAILED] HTTP 401 Unauthorized.")
            print("   The MASTODON_ACCESS_TOKEN in .env is invalid or expired.")
            print("   Please check for any typos or extra spaces.")
            return False
        elif resp.status_code == 404:
            print(f"   [FAILED] HTTP 404 Not Found at {endpoint}.")
            print("   Check that MASTODON_INSTANCE_URL is correct.")
            return False
        else:
            err_msg = data.get("error") or resp.text
            print(f"   [FAILED] Error (HTTP {resp.status_code}): {err_msg}")
            return False

    except Exception as exc:
        print(f"   [FAILED] Connection error: {str(exc)}")
        return False


if __name__ == "__main__":
    success = verify_mastodon()
    sys.exit(0 if success else 1)
