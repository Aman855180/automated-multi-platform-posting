"""Publish live post through FastAPI endpoint POST /posting."""

import json
import os
import subprocess
import sys
import time
import httpx

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def main():
    print("=" * 65)
    print("EXECUTING LIVE PUBLISH VIA FASTAPI POST /posting")
    print("=" * 65)

    # Start uvicorn server in background
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "4000",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    try:
        # Allow server to bind
        time.sleep(2.5)

        test_payload = {
            "message": "Testing our automated multi-platform posting system live on Telegram! Visit our website: https://example.com"
        }

        print(f"\n1. Sending request to http://127.0.0.1:4000/posting ...")
        print(f"   Payload: {json.dumps(test_payload, indent=2)}")

        with httpx.Client(timeout=15.0) as client:
            resp = client.post("http://127.0.0.1:4000/posting", json=test_payload)
            print(f"\n2. Server Response (HTTP {resp.status_code}):")
            data = resp.json()
            print(json.dumps(data, indent=2))

            # Inspect Telegram specific result
            telegram_result = next(
                (r for r in data.get("results", []) if r.get("platform") == "Telegram"), None
            )

            print("\n3. Telegram Publication Audit:")
            if telegram_result:
                status = telegram_result.get("status")
                posted_url = telegram_result.get("posted_url")
                public_access = telegram_result.get("public_access")
                error = telegram_result.get("error")

                print(f"   Status:        {status}")
                print(f"   Posted URL:    {posted_url}")
                print(f"   Public Access: {public_access}")
                print(f"   Date:          {telegram_result.get('date')}")
                print(f"   Time:          {telegram_result.get('time')}")
                print(f"   Error:         {error}")

                if status == "success" and posted_url:
                    print("\n" + "=" * 65)
                    print("LIVE POSTING SUCCESSFUL!")
                    print(f"Visit your post in Telegram: {posted_url}")
                    print("=" * 65)
                else:
                    print(f"\n[FAILED] Posting failed with error: {error}")
            else:
                print("\n[ERROR] Telegram was not present in the results list.")

    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
