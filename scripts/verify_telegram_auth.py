"""Safe verification script for Telegram Bot Authentication and Channel Access.

Does NOT publish any message. Only tests:
1. `getMe` - Confirms the bot token is valid.
2. `getChat` - Confirms the channel exists and the bot can access it.
"""

import os
import sys

# Ensure root project directory is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import httpx
from app.config import Settings


def verify_telegram():
    config = Settings()
    bot_token = config.TELEGRAM_BOT_TOKEN
    chat_id = config.TELEGRAM_CHAT_ID

    print("=" * 65)
    print("TELEGRAM SAFE AUTHENTICATION TEST")
    print("=" * 65)

    if not bot_token or not bot_token.strip():
        print("\n[ERROR] TELEGRAM_BOT_TOKEN is missing or blank in .env.")
        print("Please open .env and set: TELEGRAM_BOT_TOKEN=your_token_here")
        return False

    if not chat_id or not chat_id.strip():
        print("\n[ERROR] TELEGRAM_CHAT_ID is missing or blank in .env.")
        print("Please open .env and set: TELEGRAM_CHAT_ID=@your_channel_username")
        return False

    # Mask token for security in display (never print secrets)
    masked_token = bot_token[:6] + "..." + bot_token[-4:] if len(bot_token) > 10 else "***"
    print(f"\n1. Loaded configuration:")
    print(f"   Bot Token: {masked_token}")
    print(f"   Chat ID:   {chat_id}")

    # Check 1: Verify Bot Token via `getMe`
    print("\n2. Contacting Telegram API: getMe...")
    try:
        resp = httpx.get(f"https://api.telegram.org/bot{bot_token}/getMe", timeout=10.0)
        data = resp.json()

        if resp.status_code == 200 and data.get("ok"):
            bot_info = data.get("result", {})
            print(f"   [SUCCESS] Bot token is valid!")
            print(f"   Bot Name:     {bot_info.get('first_name')}")
            print(f"   Bot Username: @{bot_info.get('username')}")
        elif resp.status_code == 401:
            print("   [FAILED] HTTP 401 Unauthorized.")
            print("   The TELEGRAM_BOT_TOKEN in .env is invalid or expired.")
            print("   Please check for any typos or extra spaces.")
            return False
        elif resp.status_code == 404:
            print("   [FAILED] HTTP 404 Not Found.")
            print("   The TELEGRAM_BOT_TOKEN format is incorrect.")
            return False
        else:
            print(f"   [FAILED] Error: {data.get('description', resp.text)}")
            return False
    except Exception as exc:
        print(f"   [FAILED] Connection error: {str(exc)}")
        return False

    # Check 2: Verify Channel Access via `getChat`
    print("\n3. Verifying Channel Access: getChat...")
    try:
        resp = httpx.get(
            f"https://api.telegram.org/bot{bot_token}/getChat",
            params={"chat_id": chat_id},
            timeout=10.0,
        )
        data = resp.json()

        if resp.status_code == 200 and data.get("ok"):
            chat_info = data.get("result", {})
            print(f"   [SUCCESS] Channel found and accessible!")
            print(f"   Channel Title:    {chat_info.get('title')}")
            print(f"   Channel Username: @{chat_info.get('username')}")
            print(f"   Channel Type:     {chat_info.get('type')}")
        elif resp.status_code == 400:
            print(f"   [FAILED] HTTP 400: {data.get('description', '')}")
            print("   Common causes:")
            print("   - The channel username has a typo (make sure to include '@' like @my_channel).")
            print("   - The bot has not been added as an Administrator to the channel yet.")
            return False
        else:
            print(f"   [FAILED] Error: {data.get('description', resp.text)}")
            return False

    except Exception as exc:
        print(f"   [FAILED] Connection error: {str(exc)}")
        return False

    print("\n" + "=" * 65)
    print("ALL TELEGRAM AUTHENTICATION CHECKS PASSED!")
    print("Your bot is verified and ready to post to your channel.")
    print("=" * 65)
    return True


if __name__ == "__main__":
    success = verify_telegram()
    sys.exit(0 if success else 1)
