# MISSION: PIPELINE AGENT (PHASE 2 SIMPLIFIED - NO PHOTON/SLACK)

You are the Pipeline Agent for "The Engineering Historian". Phase 1 (Memory & Dify) is verified and running. 

The user wants to skip external webhooks (Slack/GitHub) and the Photon delivery agent for now. We will build a simplified ingestion pipeline that uses direct REST endpoints and a local CLI instead. We will add the Photon iMessage interface later.

## CONTEXT
Read `/Users/shanyu/Documents/Study/ContextCortex/production_artifacts/IMPLEMENTATION_PLAN.md` for the data models, but **IGNORE** the webhook and Slack bot instructions.

## YOUR OBJECTIVE
Implement the simplified Ingestion Service inside `services/ingestion/` and a local CLI.

1. **Manual Ingestion Endpoints (`app/main.py`)**:
   - `POST /api/v1/ingest_message`: Accepts `{"user": "...", "text": "...", "thread_id": "..."}`.
   - `POST /api/v1/simulate_pr`: Accepts `{"author": "...", "code_diff": "...", "file_paths": [...]}`.
   - These endpoints push the payload to the Redis queue.

2. **Extraction Worker (`app/worker.py`)**:
   - Use Redis (already running on port 6379).
   - For message events: Use **GMI Cloud** (Kimi-k2) to extract "Knowledge Triples" (Subject, Predicate, Object) and store them via the Memory Service.
   - For PR events: Call the Memory Service `/api/v1/check` endpoint. If a conflict is found, **log the alert to the console/stdout** (do not use Slack/Photon).

3. **Demo Seeding & CLI (`scripts/seed_demo.py` & `scripts/cli.py`)**:
   - Update `seed_demo.py` to populate HydraDB with the initial "Historical Context" (e.g., the decision to use JWT).
   - Create a simple `scripts/cli.py` that lets the user type a message or simulate a PR from their terminal, hitting the local endpoints.

## EXECUTION RULES
- Use `GMI_API_KEY` and `REDIS_URL` from the local `.env`.
- Ensure the extraction logic has a confidence threshold filter (>0.7).
- No Slack SDKs, no Photon SDKs, no GitHub webhook validation. Keep it purely local HTTP + Redis.
