"""Dev.to API Key Verification Script.

Tests GET https://dev.to/api/users/me with your DEVTO_API_KEY
to confirm credentials are valid without creating any articles.
"""

import asyncio
import os
import sys

import httpx

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.config import settings


async def verify_devto() -> None:
    if not settings.DEVTO_API_KEY:
        print("[FAIL] DEVTO_API_KEY is not set in .env")
        print("Please add DEVTO_API_KEY to your .env file.")
        return

    print("Verifying Dev.to API connection (read-only)...")
    headers = {
        "api-key": settings.DEVTO_API_KEY.strip(),
        "Accept": "application/vnd.forem.api-v1+json",
        "User-Agent": "automated-posting:v1.0.0",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://dev.to/api/users/me", headers=headers)

        if resp.status_code == 200:
            data = resp.json()
            username = data.get("username", "N/A")
            name = data.get("name", "N/A")
            profile_url = f"https://dev.to/{username}"
            print(f"[SUCCESS] Dev.to connected successfully!")
            print(f"  Name:        {name}")
            print(f"  Username:    @{username}")
            print(f"  Profile URL: {profile_url}")
        elif resp.status_code == 401:
            print("[FAIL] Unauthorized (401). Invalid or expired DEVTO_API_KEY.")
        else:
            print(f"[FAIL] Dev.to returned status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")


if __name__ == "__main__":
    asyncio.run(verify_devto())
