"""Live audit script to verify real Uvicorn server endpoints."""

import json
import subprocess
import sys
import time
import httpx

SERVER_URL = "http://127.0.0.1:4000"


def main():
    print("=" * 70)
    print("STARTING LIVE UVICORN SERVER AUDIT")
    print("=" * 70)

    # Start uvicorn subprocess
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
        # Wait for server to bind
        time.sleep(2.5)

        with httpx.Client(base_url=SERVER_URL, timeout=10.0) as client:
            # 1. Test GET /health
            print("\n[TEST 1] GET /health")
            resp_health = client.get("/health")
            print(f"Status Code: {resp_health.status_code}")
            print("Response Body:")
            print(json.dumps(resp_health.json(), indent=2))
            assert resp_health.status_code == 200
            assert resp_health.json()["status"] == "healthy"

            # 2. Test GET /docs
            print("\n[TEST 2] GET /docs (OpenAPI Swagger UI)")
            resp_docs = client.get("/docs")
            print(f"Status Code: {resp_docs.status_code}")
            print(f"Content-Type: {resp_docs.headers.get('content-type')}")
            print(f"HTML Length: {len(resp_docs.text)} bytes")
            assert resp_docs.status_code == 200
            assert "swagger-ui" in resp_docs.text.lower()

            # 3. Test POST /posting with valid input (no credentials in .env)
            print("\n[TEST 3] POST /posting with valid input (unconfigured credentials)")
            valid_payload = {
                "message": "Check out our latest business platform and grow your online visibility. https://example.com"
            }
            resp_post = client.post("/posting", json=valid_payload)
            print(f"Status Code: {resp_post.status_code}")
            print("Response Body:")
            print(json.dumps(resp_post.json(), indent=2))
            assert resp_post.status_code == 200
            data = resp_post.json()
            assert data["success"] is False
            assert len(data["results"]) == 5
            for r in data["results"]:
                assert r["status"] == "failed"
                assert "Missing credentials" in r["error"]

            # 4. Test POST /posting with invalid input (no URL)
            print("\n[TEST 4] POST /posting with invalid input (no URL -> 422)")
            no_url_payload = {"message": "Message without any link whatsoever"}
            resp_no_url = client.post("/posting", json=no_url_payload)
            print(f"Status Code: {resp_no_url.status_code}")
            print("Response Body:")
            print(json.dumps(resp_no_url.json(), indent=2))
            assert resp_no_url.status_code == 422

            # 5. Test POST /posting with invalid input (> 200 chars)
            print("\n[TEST 5] POST /posting with invalid input (> 200 chars -> 422)")
            long_payload = {"message": "A" * 195 + " https://example.com"}
            resp_long = client.post("/posting", json=long_payload)
            print(f"Status Code: {resp_long.status_code}")
            print("Response Body:")
            print(json.dumps(resp_long.json(), indent=2))
            assert resp_long.status_code == 422

            # 6. Test POST /posting with invalid input (multiple URLs)
            print("\n[TEST 6] POST /posting with invalid input (multiple URLs -> 422)")
            multi_url_payload = {
                "message": "Visit https://site1.com or https://site2.com for details"
            }
            resp_multi = client.post("/posting", json=multi_url_payload)
            print(f"Status Code: {resp_multi.status_code}")
            print("Response Body:")
            print(json.dumps(resp_multi.json(), indent=2))
            assert resp_multi.status_code == 422

        print("\n" + "=" * 70)
        print("ALL LIVE SERVER AUDIT CHECKS PASSED SUCCESSFULLY!")
        print("=" * 70)

    finally:
        proc.terminate()
        proc.wait(timeout=5)


if __name__ == "__main__":
    main()
