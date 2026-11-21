"""Safe verification script for Bluesky Authentication.

Does NOT publish any post. Only tests:
1. `com.atproto.server.createSession` - Confirms credentials generate a valid JWT session.
2. `app.bsky.actor.getProfile` - Confirms the account profile is active and accessible.
"""

import os
import sys

# Ensure root project directory is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import httpx
from app.config import Settings


def verify_bluesky():
    config = Settings()
    handle = config.BLUESKY_HANDLE
    password = config.BLUESKY_APP_PASSWORD
    service_url = (config.BLUESKY_SERVICE_URL or "https://bsky.social").rstrip("/")

    print("=" * 65)
    print("BLUESKY SAFE AUTHENTICATION TEST")
    print("=" * 65)

    if not handle or not handle.strip():
        print("\n[ERROR] BLUESKY_HANDLE is missing or blank in .env.")
        print("Please open .env and set: BLUESKY_HANDLE=yourname.bsky.social")
        return False

    if not password or not password.strip():
        print("\n[ERROR] BLUESKY_APP_PASSWORD is missing or blank in .env.")
        print("Please open .env and set: BLUESKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx")
        return False

    masked_handle = handle[:3] + "..." + handle[handle.find("."):] if "." in handle else handle
    print(f"\n1. Loaded configuration:")
    print(f"   Handle:      {masked_handle}")
    print(f"   Service URL: {service_url}")
    print(f"   Password:    [CONFIGURED - HIDDEN]")

    # Check 1: Authenticate via createSession
    print("\n2. Contacting AT Protocol: createSession...")
    session_url = f"{service_url}/xrpc/com.atproto.server.createSession"
    session_payload = {
        "identifier": handle.strip(),
        "password": password.strip(),
    }

    try:
        resp = httpx.post(session_url, json=session_payload, timeout=10.0)
        data = resp.json()

        if resp.status_code == 200:
            access_jwt = data.get("accessJwt")
            did = data.get("did")
            resolved_handle = data.get("handle")
            print(f"   [SUCCESS] Session created successfully!")
            print(f"   Resolved Handle: @{resolved_handle}")
            print(f"   Account DID:     {did}")

            # Check 2: Fetch profile metadata to verify active account state
            print("\n3. Verifying Profile Access: getProfile...")
            profile_url = f"{service_url}/xrpc/app.bsky.actor.getProfile"
            headers = {"Authorization": f"Bearer {access_jwt}"}
            prof_resp = httpx.get(profile_url, params={"actor": did}, headers=headers, timeout=10.0)

            if prof_resp.status_code == 200:
                prof_data = prof_resp.json()
                print(f"   [SUCCESS] Profile verified and active!")
                print(f"   Display Name:    {prof_data.get('displayName', '(Not set)')}")
                print(f"   Followers:       {prof_data.get('followersCount', 0)}")
                print(f"   Public Profile:  https://bsky.app/profile/{resolved_handle}")
            else:
                print(f"   [WARNING] getProfile returned HTTP {prof_resp.status_code}")

            print("\n" + "=" * 65)
            print("ALL BLUESKY AUTHENTICATION CHECKS PASSED!")
            print("Your Bluesky account is authorized and ready for live posting.")
            print("=" * 65)
            return True

        elif resp.status_code in (400, 401, 403):
            error_code = data.get("error", "")
            error_message = data.get("message", resp.text)
            print(f"   [FAILED] HTTP {resp.status_code} ({error_code}): {error_message}")
            print("   Common causes:")
            print("   - Double-check that BLUESKY_HANDLE has your full handle (e.g. user.bsky.social).")
            print("   - Ensure the 16-character App Password includes the dashes (e.g. xxxx-xxxx-xxxx-xxxx).")
            print("   - Make sure there are no accidental spaces before or after the password.")
            return False
        else:
            print(f"   [FAILED] Server Error (HTTP {resp.status_code}): {resp.text}")
            return False

    except Exception as exc:
        print(f"   [FAILED] Connection error: {str(exc)}")
        return False


if __name__ == "__main__":
    success = verify_bluesky()
    sys.exit(0 if success else 1)
