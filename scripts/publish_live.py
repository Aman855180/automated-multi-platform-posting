"""Execute real live post across all configured platforms via FastAPI POST /posting."""

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
            "message": "Testing automated multi-platform posting live across 5 platforms: Telegram, Bluesky, Mastodon, Discord, and Dev.to! https://example.com"
        }

        print(f"\n1. Sending request to http://127.0.0.1:4000/posting ...")
        print(f"   Payload: {json.dumps(test_payload, indent=2)}")

        with httpx.Client(timeout=20.0) as client:
            resp = client.post("http://127.0.0.1:4000/posting", json=test_payload)
            print(f"\n2. Server Response (HTTP {resp.status_code}):")
            data = resp.json()
            print(json.dumps(data, indent=2))

            print("\n3. Live Platform Results Breakdown:")
            for r in data.get("results", []):
                p_name = r.get("platform")
                p_status = r.get("status")
                p_url = r.get("posted_url")
                p_public = r.get("public_access")
                p_err = r.get("error")

                if p_status == "success":
                    print(f"   [SUCCESS] {p_name}:")
                    print(f"             URL:           {p_url}")
                    print(f"             Public Access: {p_public}")
                    print(f"             Date / Time:   {r.get('date')} {r.get('time')}")
                else:
                    print(f"   [FAILED]  {p_name}: {p_err}")

        print("\n" + "=" * 65)
        print("LIVE PUBLISHING COMPLETED!")
        print("=" * 65)

    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
