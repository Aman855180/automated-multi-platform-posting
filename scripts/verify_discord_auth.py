"""Discord Webhook Verification Script.

Tests GET <DISCORD_WEBHOOK_URL> to confirm the webhook is valid
without posting any message to your channel.
"""

import asyncio
import os
import sys

import httpx

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from app.config import settings


async def verify_discord() -> None:
    if not settings.DISCORD_WEBHOOK_URL:
        print("[FAIL] DISCORD_WEBHOOK_URL is not set in .env")
        print("Please add DISCORD_WEBHOOK_URL to your .env file.")
        return

    print("Verifying Discord Webhook connection (read-only)...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(settings.DISCORD_WEBHOOK_URL)

        if resp.status_code == 200:
            data = resp.json()
            name = data.get("name", "Unknown Webhook")
            channel_id = data.get("channel_id", "N/A")
            guild_id = data.get("guild_id", "N/A")
            print(f"[SUCCESS] Discord Webhook connected!")
            print(f"  Webhook Name: {name}")
            print(f"  Channel ID:   {channel_id}")
            print(f"  Guild/Server: {guild_id}")
            if not settings.DISCORD_SERVER_ID and guild_id != "N/A":
                print(f"\n[TIP] You can also add DISCORD_SERVER_ID={guild_id} to .env for direct post URLs!")
        elif resp.status_code == 404:
            print("[FAIL] Webhook not found (404). Please verify your DISCORD_WEBHOOK_URL.")
        else:
            print(f"[FAIL] Discord returned status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[ERROR] Failed to connect: {e}")


if __name__ == "__main__":
    asyncio.run(verify_discord())
