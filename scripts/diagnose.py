import os
import redis
import httpx
import asyncio
from dotenv import load_dotenv

def diagnose():
    print("--- Environment Diagnostic ---")
    # Try multiple ways to find .env
    possible_paths = [
        ".env",
        "../.env",
        "../../.env",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    ]
    
    env_found = False
    for p in possible_paths:
        if os.path.exists(p):
            print(f"Found .env at: {p}")
            load_dotenv(p)
            env_found = True
            break
    
    if not env_found:
        print("Error: .env file not found anywhere!")

    keys_to_check = ["GMI_API_KEY", "MEMORY_SERVICE_API_KEY", "REDIS_URL"]
    for key in keys_to_check:
        val = os.environ.get(key)
        if val:
            print(f"Check {key}: FOUND ({val[:10]}...)")
        else:
            print(f"Check {key}: MISSING")

    print("\n--- Redis Diagnostic ---")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    print(f"Testing Redis at: {redis_url}")
    try:
        r = redis.from_url(redis_url)
        r.ping()
        print("Redis Status: CONNECTED")
    except Exception as e:
        print(f"Redis Status: FAILED ({str(e)})")

    print("\n--- Memory Service Diagnostic ---")
    mem_url = os.environ.get("MEMORY_SERVICE_URL", "http://localhost:8000")
    print(f"Testing Memory Service at: {mem_url}")
    try:
        # We don't use async here for simplicity in a quick script
        import requests
        resp = requests.get(f"{mem_url}/health", timeout=2)
        print(f"Memory Service Status: {resp.status_code} - {resp.json()}")
    except Exception as e:
        print(f"Memory Service Status: FAILED ({str(e)})")

if __name__ == "__main__":
    diagnose()
