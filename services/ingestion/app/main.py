import os
import json
import redis
from fastapi import FastAPI, HTTPException, status
from .models import IngestMessageRequest, SimulatePRRequest
# Load .env from root
import os
from dotenv import load_dotenv
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
dotenv_path = os.path.join(root_dir, ".env.agent")
load_dotenv(dotenv_path)

app = FastAPI(title="ContextCortex Ingestion Service", version="1.0.0")

# File-based queue instead of Redis
QUEUE_FILE = os.path.join(root_dir, "ingestion_queue.json")

def push_to_queue(queue_name, data):
    try:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, "r") as f:
                queue = json.load(f)
        else:
            queue = {}
        
        if queue_name not in queue:
            queue[queue_name] = []
        queue[queue_name].append(data)
        
        with open(QUEUE_FILE, "w") as f:
            json.dump(queue, f)
    except Exception as e:
        print(f"Queue Error: {e}")

@app.get("/health")
async def health():
    return {"status": "ok", "queue": "file-based"}

@app.post("/api/v1/ingest_message", status_code=status.HTTP_202_ACCEPTED)
async def ingest_message(request: IngestMessageRequest):
    try:
        payload = request.model_dump()
        push_to_queue("messages", payload)
        return {"status": "queued", "queue": "file:messages"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/simulate_pr", status_code=status.HTTP_202_ACCEPTED)
async def simulate_pr(request: SimulatePRRequest):
    try:
        payload = request.model_dump()
        push_to_queue("prs", payload)
        return {"status": "queued", "queue": "file:prs"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8011))
    uvicorn.run(app, host="0.0.0.0", port=port)
