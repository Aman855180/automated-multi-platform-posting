"""Safe verification script for Reddit Authentication.

Does NOT publish any post. Only tests:
1. `https://www.reddit.com/api/v1/access_token` - Confirms OAuth credentials and password grant token exchange.
2. `https://oauth.reddit.com/api/v1/me` - Confirms the authenticated account identity.
"""

import os
import sys

# Ensure root project directory is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import httpx
from app.config import Settings


def verify_reddit():
    config = Settings()
    client_id = config.REDDIT_CLIENT_ID
    client_secret = config.REDDIT_CLIENT_SECRET
    username = config.REDDIT_USERNAME
    password = config.REDDIT_PASSWORD
    subreddit = config.REDDIT_SUBREDDIT or "test"
    user_agent = config.REDDIT_USER_AGENT or f"automated-posting:v1.0.0 (by /u/{username or 'user'})"

    print("=" * 65)
    print("REDDIT SAFE AUTHENTICATION TEST")
    print("=" * 65)

    missing = []
    if not client_id:
        missing.append("REDDIT_CLIENT_ID")
    if not client_secret:
        missing.append("REDDIT_CLIENT_SECRET")
    if not username:
        missing.append("REDDIT_USERNAME")
    if not password:
        missing.append("REDDIT_PASSWORD")

    if missing:
        print("\n[ERROR] Missing required Reddit credentials in .env:")
        for m in missing:
            print(f"   - {m}")
        return False

    masked_cid = client_id[:4] + "..." if len(client_id) > 6 else "***"
    print(f"\n1. Loaded configuration:")
    print(f"   Client ID:     {masked_cid}")
    print(f"   Username:      /u/{username}")
    print(f"   Subreddit:     r/{subreddit}")
    print(f"   User-Agent:    {user_agent}")
    print(f"   Client Secret: [CONFIGURED - HIDDEN]")
    print(f"   Password:      [CONFIGURED - HIDDEN]")

    # Check 1: Token Exchange
    print("\n2. Exchanging OAuth2 Token (grant_type=password)...")
    token_url = "https://www.reddit.com/api/v1/access_token"
    token_auth = (client_id.strip(), client_secret.strip())
    token_data = {
        "grant_type": "password",
        "username": username.strip(),
        "password": password.strip(),
    }
    token_headers = {"User-Agent": user_agent}

    try:
        resp = httpx.post(token_url, auth=token_auth, data=token_data, headers=token_headers, timeout=10.0)

        data = {}
        try:
            data = resp.json()
        except Exception:
            pass

        if resp.status_code == 200 and "access_token" in data:
            access_token = data.get("access_token")
            scope = data.get("scope", "")
            print("   [SUCCESS] OAuth2 token exchange successful!")
            print(f"   Token Type: {data.get('token_type')}")
            print(f"   Token Scope: {scope or 'all'}")

            # Check 2: Account Identity via /api/v1/me
            print("\n3. Verifying Identity via /api/v1/me...")
            me_url = "https://oauth.reddit.com/api/v1/me"
            me_headers = {
                "Authorization": f"bearer {access_token}",
                "User-Agent": user_agent,
            }
            me_resp = httpx.get(me_url, headers=me_headers, timeout=10.0)

            if me_resp.status_code == 200:
                me_data = me_resp.json()
                print(f"   [SUCCESS] Authenticated Reddit user confirmed!")
                print(f"   Username:     u/{me_data.get('name')}")
                print(f"   Account ID:   t2_{me_data.get('id')}")
                print(f"   Total Karma:  {me_data.get('total_karma', 0)}")
            else:
                print(f"   [WARNING] /api/v1/me returned HTTP {me_resp.status_code}")

            print("\n" + "=" * 65)
            print("ALL REDDIT AUTHENTICATION CHECKS PASSED!")
            print("Your Reddit account is authorized and ready for live posting.")
            print("=" * 65)
            return True

        elif resp.status_code == 401:
            print("   [FAILED] HTTP 401 Unauthorized.")
            print("   Your REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET is incorrect.")
            return False
        elif resp.status_code == 403:
            print("   [FAILED] HTTP 403 Forbidden.")
            print("   Your REDDIT_USER_AGENT was blocked by Reddit, or API access is blocked.")
            return False
        elif "error" in data:
            err = data.get("error")
            print(f"   [FAILED] Reddit OAuth error: {err}")
            if err == "invalid_grant":
                print("   Explanation for 'invalid_grant':")
                print("   - Username or password might be incorrect.")
                print("   - Your account might have Two-Factor Authentication (2FA) enabled.")
                print("     (Reddit password grant does not work with 2FA enabled accounts).")
            return False
        else:
            print(f"   [FAILED] Error (HTTP {resp.status_code}): {resp.text}")
            return False

    except Exception as exc:
        print(f"   [FAILED] Connection error: {str(exc)}")
        return False


if __name__ == "__main__":
    success = verify_reddit()
    sys.exit(0 if success else 1)
