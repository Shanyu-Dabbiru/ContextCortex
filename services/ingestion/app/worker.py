import os
import json
import asyncio
import redis.asyncio as redis
import httpx
from openai import AsyncOpenAI
from .models import IngestMessageRequest, SimulatePRRequest
from dotenv import load_dotenv
import structlog

# Load .env from root
import os
from dotenv import load_dotenv
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
dotenv_path = os.path.join(root_dir, ".env.agent")
load_dotenv(dotenv_path)

# Logger
logger = structlog.get_logger()

# Config
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
GMI_API_KEY = os.environ.get("GMI_API_KEY")
if not GMI_API_KEY:
    raise ValueError("GMI_API_KEY not found in environment")
GMI_API_BASE = os.environ.get("GMI_API_BASE", "https://api.gmicloud.ai/v1")
GMI_MODEL = os.environ.get("GMI_MODEL", "kimi-k2")
MEMORY_SERVICE_URL = os.environ.get("MEMORY_SERVICE_URL", "http://localhost:8000")
MEMORY_SERVICE_API_KEY = os.environ.get("MEMORY_SERVICE_API_KEY")

client = AsyncOpenAI(api_key=GMI_API_KEY, base_url=GMI_API_BASE)

EXTRACTION_PROMPT = """You are an "Engineering History" extractor. 
Analyze the following engineering discussion/message and extract "Knowledge Triples" about architectural decisions, constraints, or rationales.

A Knowledge Triple is:
- Subject: The thing being decided (type: decision, user, thread, etc.)
- Predicate: The relationship (e.g., MADE_BY, CONSTRAINED_BY, RESOLVES, VIOLATES, DISCUSSED_IN)
- Object: The target entity
- Evidence: Exact quote from the text
- Confidence: 0.0 to 1.0

Guidelines:
- If a user makes a decision, include (Decision) MADE_BY (User).
- If a decision is discussed in a thread, include (Decision) DISCUSSED_IN (Thread).
- Focus on architectural significance.

Output MUST be a JSON object with a "triples" key containing a list of objects exactly matching this schema:
{
  "triples": [
    {
      "subject": {"type": "decision", "id": "auth-jwt"},
      "predicate": "MADE_BY",
      "object": {"type": "user", "id": "shanyu"},
      "evidence": "I decided to use JWT",
      "confidence": 0.95
    }
  ]
}

Input Text:
{text}
"""

async def extract_triples(text: str):
    try:
        response = await client.chat.completions.create(
            model=GMI_MODEL,
            messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(text=text)}],
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        
        # Robust JSON cleaning (in case model adds markdown blocks)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        data = json.loads(content)
        return data.get("triples", [])
    except Exception as e:
        logger.error("extraction_failed", error=str(e), content=content if 'content' in locals() else None)
        return []

async def store_triples(triples, metadata):
    async with httpx.AsyncClient() as http_client:
        headers = {"Authorization": f"Bearer {MEMORY_SERVICE_API_KEY}"}
        for t in triples:
            if t.get("confidence", 0) < 0.7:
                logger.info("skip_low_confidence", triple=t)
                continue
            
            # 1. Upsert Nodes (Subject and Object)
            for node_key in ["subject", "object"]:
                node_data = t[node_key]
                upsert_payload = {
                    "type": node_data["type"],
                    "id": node_data["id"],
                    "data": {"source": metadata.get("source", "worker")}
                }
                await http_client.post(f"{MEMORY_SERVICE_URL}/api/v1/nodes", json=upsert_payload, headers=headers)

            # 2. Ingest Triple
            ingest_payload = {
                "subject": t["subject"],
                "predicate": t["predicate"],
                "object": t["object"],
                "metadata": {
                    "evidence": t["evidence"],
                    "confidence": t["confidence"],
                    **metadata
                }
            }
            await http_client.post(f"{MEMORY_SERVICE_URL}/api/v1/ingest", json=ingest_payload, headers=headers)
            logger.info("triple_stored", triple=t)

async def check_pr(pr_data: dict):
    async with httpx.AsyncClient() as http_client:
        headers = {"Authorization": f"Bearer {MEMORY_SERVICE_API_KEY}"}
        check_payload = {
            "author": pr_data["author"],
            "code_diff": pr_data["code_diff"],
            "file_paths": pr_data["file_paths"]
        }
        response = await http_client.post(f"{MEMORY_SERVICE_URL}/api/v1/check", json=check_payload, headers=headers)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "conflict":
                logger.warning("GHOST_REVIEW_ALERT", pr=pr_data["pr_number"], violations=result["violations"])
                print(f"\n[!] GHOST REVIEW ALERT - PR #{pr_data.get('pr_number', 'unknown')}")
                for v in result["violations"]:
                    print(f"    - Violation: {v['title']}")
                    print(f"    - Decision: {v['description']}")
                    print(f"    - Evidence: {v['evidence_quote']}\n")
            else:
                logger.info("pr_check_clean", pr=pr_data.get("pr_number"))
        else:
            logger.error("check_failed", status=response.status_code, text=response.text)

# File-based queue instead of Redis
QUEUE_FILE = os.path.join(root_dir, "ingestion_queue.json")

def pop_from_queue(queue_name):
    if not os.path.exists(QUEUE_FILE):
        return None
    try:
        with open(QUEUE_FILE, "r") as f:
            queue = json.load(f)
        
        if queue_name in queue and queue[queue_name]:
            item = queue[queue_name].pop(0)
            with open(QUEUE_FILE, "w") as f:
                json.dump(queue, f)
            return item
    except Exception as e:
        logger.error("queue_error", error=str(e))
    return None

async def main():
    logger.info("worker_started", queue="file-based")
    
    while True:
        # Check messages
        msg = pop_from_queue("messages")
        if msg:
            logger.info("processing_message", user=msg["user"])
            triples = await extract_triples(msg["text"])
            await store_triples(triples, {"source": "slack_simulation", "user": msg["user"], "thread_id": msg["thread_id"]})
        
        # Check PRs
        pr = pop_from_queue("prs")
        if pr:
            logger.info("processing_pr", author=pr["author"])
            await check_pr(pr)
            
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())
