import os
import httpx
import asyncio
from dotenv import load_dotenv

# Load .env from root
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
dotenv_path = os.path.join(root_dir, ".env.agent")
load_dotenv(dotenv_path)

MEMORY_SERVICE_URL = os.environ.get("MEMORY_SERVICE_URL", "http://localhost:8010")
MEMORY_SERVICE_API_KEY = os.environ.get("MEMORY_SERVICE_API_KEY")

DEMO_NODES = [
    {"type": "user", "id": "shanyu", "data": {"name": "Shanyu", "github_handle": "shanyu-d"}},
    {"type": "user", "id": "alex", "data": {"name": "Alex Chen", "github_handle": "alexc"}},
    {"type": "decision", "id": "auth-jwt-over-sessions", "data": {
        "title": "Use JWT tokens instead of server-side sessions",
        "description": "JWT chosen because services A, B, C don't share a session store. Stateless auth required for microservice boundary."
    }},
    {"type": "thread", "id": "slack-arch-1710502200", "data": {
        "platform": "slack", "channel": "#architecture",
        "summary": "Discussion on auth strategy for new microservice arch. Shanyu proposed JWT, team agreed."
    }}
]

DEMO_TRIPLES = [
    {
        "subject": {"type": "decision", "id": "auth-jwt-over-sessions"},
        "predicate": "MADE_BY",
        "object": {"type": "user", "id": "shanyu"},
        "metadata": {"evidence": "Shanyu proposed JWT", "confidence": 0.95}
    },
    {
        "subject": {"type": "decision", "id": "auth-jwt-over-sessions"},
        "predicate": "DISCUSSED_IN",
        "object": {"type": "thread", "id": "slack-arch-1710502200"},
        "metadata": {"evidence": "#architecture discussion", "confidence": 0.95}
    }
]

async def seed():
    headers = {"Authorization": f"Bearer {MEMORY_SERVICE_API_KEY}"}
    async with httpx.AsyncClient() as client:
        print("--- Seeding Nodes ---")
        for node in DEMO_NODES:
            resp = await client.post(f"{MEMORY_SERVICE_URL}/api/v1/nodes", json=node, headers=headers)
            print(f"Node {node['id']}: {resp.status_code}")

        print("\n--- Seeding Triples ---")
        for triple in DEMO_TRIPLES:
            resp = await client.post(f"{MEMORY_SERVICE_URL}/api/v1/ingest", json=triple, headers=headers)
            print(f"Triple {triple['subject']['id']} -> {triple['predicate']} -> {triple['object']['id']}: {resp.status_code}")

if __name__ == "__main__":
    asyncio.run(seed())
