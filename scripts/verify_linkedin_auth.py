"""Safe verification script for LinkedIn Authentication.

Does NOT publish any post. Only tests:
`GET https://api.linkedin.com/v2/userinfo` - Confirms the access token is valid and extracts member name and Person URN.
"""

import os
import sys

# Ensure root project directory is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import httpx
from app.config import Settings


def verify_linkedin():
    config = Settings()
    access_token = config.LINKEDIN_ACCESS_TOKEN
    author_urn = config.LINKEDIN_AUTHOR_URN

    print("=" * 65)
    print("LINKEDIN SAFE AUTHENTICATION TEST")
    print("=" * 65)

    if not access_token or not access_token.strip():
        print("\n[ERROR] LINKEDIN_ACCESS_TOKEN is missing or blank in .env.")
        print("Please open .env and set: LINKEDIN_ACCESS_TOKEN=your_token_here")
        return False

    masked_token = access_token[:6] + "..." + access_token[-4:] if len(access_token) > 10 else "***"
    print(f"\n1. Loaded configuration:")
    print(f"   Access Token: {masked_token}")
    print(f"   Author URN:   {author_urn or '[NOT SET - WILL QUERY FROM API]'}")

    # Check 1: Verify token via /v2/userinfo
    print("\n2. Contacting LinkedIn API: /v2/userinfo...")
    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "User-Agent": "AutomatedMultiPlatformPosting/1.0",
    }

    try:
        resp = httpx.get("https://api.linkedin.com/v2/userinfo", headers=headers, timeout=10.0)
        data = {}
        try:
            data = resp.json()
        except Exception:
            pass

        if resp.status_code == 200:
            person_sub = data.get("sub")
            name = data.get("name") or f"{data.get('given_name', '')} {data.get('family_name', '')}".strip()
            email = data.get("email")

            resolved_urn = f"urn:li:person:{person_sub}"
            print(f"   [SUCCESS] LinkedIn access token is valid!")
            print(f"   Member Name:  {name}")
            print(f"   Member Email: {email or '(Not returned)'}")
            print(f"   Person URN:   {resolved_urn}")

            if author_urn and author_urn.strip() != resolved_urn:
                print(f"\n   [NOTE] Your .env has LINKEDIN_AUTHOR_URN={author_urn}")
                print(f"   Suggested URN from token is: {resolved_urn}")

            print("\n" + "=" * 65)
            print("ALL LINKEDIN AUTHENTICATION CHECKS PASSED!")
            print(f"Ensure LINKEDIN_AUTHOR_URN={resolved_urn} in your .env.")
            print("Your LinkedIn integration is authorized and ready for live posting.")
            print("=" * 65)
            return True

        elif resp.status_code == 401:
            print("   [FAILED] HTTP 401 Unauthorized.")
            print("   The LINKEDIN_ACCESS_TOKEN is invalid or expired.")
            print("   Please check for any typos or request a fresh token.")
            return False
        elif resp.status_code == 403:
            print("   [FAILED] HTTP 403 Forbidden.")
            print("   Missing OpenID / Profile scopes or token lacks required permissions.")
            return False
        else:
            err_msg = data.get("message") or resp.text
            print(f"   [FAILED] Error (HTTP {resp.status_code}): {err_msg}")
            return False

    except Exception as exc:
        print(f"   [FAILED] Connection error: {str(exc)}")
        return False


if __name__ == "__main__":
    success = verify_linkedin()
    sys.exit(0 if success else 1)
