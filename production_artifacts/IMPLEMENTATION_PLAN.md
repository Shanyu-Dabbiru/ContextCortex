# The Engineering Historian — Comprehensive Implementation Plan

> **Team:** Solo (Shanyu)  
> **Demo Target:** "The Ghost Review" — proactive constraint detection + "Why?" recall  
> **All API keys available:** HydraDB, GMI Cloud, Photon, Dify

---

## Execution Strategy: Agent Orchestration

```mermaid
gantt
    title Build Order & Agent Parallelism
    dateFormat X
    axisFormat %s
    
    section Phase 0 — Foundation
    Directory Scaffold + .env        :p0a, 0, 1
    Docker Compose (Redis+Postgres)  :p0b, 0, 1
    
    section Phase 1 — Parallel Track A (Data Engineer)
    HydraDB Schema Init              :p1a, 1, 2
    Memory Service (FastAPI)          :p1b, 2, 4
    Memory Service Tests              :p1c, 4, 5
    
    section Phase 1 — Parallel Track B (Infra Lead)
    Dify Self-Hosted Setup            :p1d, 1, 2
    GMI Cloud Model Provider Config   :p1e, 2, 3
    Dify DSL Import + Wiring          :p1f, 3, 4
    
    section Phase 2 — Sequential (depends on 1A+1B)
    Ingestion Workers (Slack+GitHub)  :p2a, 5, 7
    Seed Demo Data (15 triples)      :p2b, 7, 8
    
    section Phase 3 — Sequential (depends on 2)
    Photon/Slack Delivery             :p3a, 8, 9
    End-to-End Integration Test       :p3b, 9, 10
    
    section Phase 4 — Demo Polish
    Demo Script + Recording           :p4a, 10, 11
```

### Agent Assignment Table

| Agent | Scope | Depends On | Can Parallelize With |
|:------|:------|:-----------|:---------------------|
| **Foundation Agent** | Phase 0: scaffolding, `.env`, `docker-compose.yml` | Nothing | — (runs first, fast) |
| **Data Engineer Agent** | Phase 1A: schema init, FastAPI memory service, tests | Phase 0 | Infra Lead (Phase 1B) |
| **Infra Lead Agent** | Phase 1B: Dify setup, GMI provider, DSL import | Phase 0 | Data Engineer (Phase 1A) |
| **Pipeline Agent** | Phase 2: ingestion workers, seed script | Phase 1A + 1B | — (sequential) |
| **Integration Agent** | Phase 3: Photon delivery, E2E tests | Phase 2 | — (sequential) |
| **Demo Agent** | Phase 4: demo script, recording | Phase 3 | — (sequential) |

---

## Phase 0: Foundation (Sequential — runs first, ~15 min)

### What it builds
The scaffolding every subsequent agent depends on. No business logic — just structure, secrets, and container orchestration.

### File Manifest

#### [NEW] `.env.example`
Every secret the system needs. Execution agent copies to `.env` and user fills in real keys.
```bash
# === GMI Cloud (Inference) ===
GMI_API_KEY=gmi_sk_...
GMI_API_BASE=https://api.gmicloud.ai/v1
GMI_MODEL=kimi-k2
EMBEDDING_DIM=768

# === HydraDB (Memory) ===
HYDRADB_API_KEY=hdb_...
HYDRADB_BASE_URL=https://<project>.hydradb.com/v1
MEMORY_BACKEND=postgres   # postgres | hydradb

# === Memory Service (Auth) ===
MEMORY_SERVICE_API_KEY=msk_...

# === Photon (Messaging) ===
PHOTON_API_KEY=ptn_...

# === Slack (Webhooks + Bot) ===
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
SLACK_CHANNEL_ID=C04A2B3...

# === GitHub (Webhooks) ===
GITHUB_WEBHOOK_SECRET=...

# === Tunneling (Dev only) ===
NGROK_AUTHTOKEN=...

# === Infrastructure ===
REDIS_URL=redis://redis:6379/0
DATABASE_URL=postgresql://cortex:cortex@postgres:5432/cortex
DIFY_API_KEY=app-...
DIFY_BASE_URL=http://localhost/v1
```

#### [NEW] `docker-compose.yml`
```yaml
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
    networks: [recall_net]

  memory-service:
    build: ./services/memory
    ports: ["8000:8000"]
    env_file: .env
    depends_on:
      redis: { condition: service_healthy }
    networks: [recall_net]

  ingestion-service:
    build: ./services/ingestion
    ports: ["8001:8001"]
    env_file: .env
    depends_on:
      memory-service: { condition: service_started }
      redis: { condition: service_healthy }
    networks: [recall_net]

networks:
  recall_net:
    driver: bridge
```

> **Networking Note (GAP A2):** Dify runs in its OWN Docker Compose. To let Dify reach `memory-service`, use `http://host.docker.internal:8000` in Dify's HTTP nodes. This works on macOS Docker Desktop. On Linux, add `--add-host=host.docker.internal:host-gateway` to Dify's compose or use a shared external Docker network.

#### [NEW] Directory structure
```
ContextCortex/
├── production_artifacts/          # Already exists (specs, DSL)
├── services/
│   ├── memory/                    # Phase 1A
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py           # FastAPI app (wrapper for HydraDB)
│   │   │   ├── models.py         # Pydantic models (strict, no Any)
│   │   │   └── hydra_client.py   # HydraDB SDK integration
│   │   ├── tests/
│   │   │   ├── test_nodes.py
│   │   │   ├── test_ingest.py
│   │   │   ├── test_recall.py
│   │   │   └── test_check.py
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── ingestion/                 # Phase 2
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py           # FastAPI webhook receiver
│   │   │   ├── slack_handler.py  # Slack Events API (+sig verify)
│   │   │   ├── github_handler.py # GitHub PR webhooks (+HMAC)
│   │   │   ├── extractor.py      # GMI-powered triple extraction
│   │   │   ├── worker.py         # Redis queue consumer (+DLQ)
│   │   │   └── proactive_checker.py  # Post-ingest → /check → Slack alert
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   └── delivery/                  # Phase 3
│       ├── app/
│       │   ├── __init__.py
│       │   └── slack_bot.py      # Slack Bot (reactive queries → Dify)
│       ├── Dockerfile
│       └── requirements.txt
├── scripts/
│   ├── seed_demo.py              # Seeds all demo triples + nodes
│   └── dify_import.sh            # Imports DSL into Dify
├── docker-compose.yml
├── .env.example
├── .env                          # User-created, git-ignored
└── .gitignore
```

### Gate Criteria (Phase 0 → Phase 1)
```bash
# All must pass before spawning Phase 1 agents:
docker compose up -d redis
docker compose ps  # "healthy"
redis-cli -h localhost ping  # PONG
```

---

## Phase 1A: Memory Service — "The Brain" (Data Engineer Agent)

> [!IMPORTANT]  
> This is the highest-risk, highest-value component. The entire demo hinges on the recall loop working. Budget 60% of development time here.

### What it builds
A FastAPI service that wraps the HydraDB SDK and exposes **4 endpoints** that the Dify chatflow and ingestion worker call.

### Detailed File Specs

#### `services/memory/app/main.py`
```
FastAPI app with 4 routes + health:

  POST /api/v1/nodes    → Upsert a node (user, decision, thread, commit, meeting)
                           1. Map node to HydraDB knowledge or user memory
                           2. Call client.upload.knowledge() or client.userMemory.add()
                           3. Return node_id + status (created/updated)

  POST /api/v1/ingest   → Store a triple (subject, predicate, object, metadata)
                           1. Store as a connection in HydraDB (embed as text relationship)
                           2. Return triple_id + status

  POST /api/v1/recall   → Given natural language query, do:
                           1. Call client.recall.fullRecall(query="...")
                           2. Extract chunks and graph_context
                           3. Return combined context

  POST /api/v1/check    → Given code diff + file_paths array, do:
                           1. Formulate semantic query from diff + files
                           2. Call client.recall.fullRecall(query=...) focused on Decisions
                           3. Score violation likelihood
                           4. Return violations with decision details + evidence

  GET  /health          → Returns {status, hydradb_connected}
```

> [!IMPORTANT]
> **GAP-12 fix:** The `/check` endpoint does NOT rely on pre-existing `VIOLATES` triples. It finds decisions constrained by the file paths, then uses **semantic similarity** between the code diff and decision descriptions to detect conflicts. The `VIOLATES` triple is created by the ingestion worker AFTER `/check` confirms a violation.

#### `services/memory/app/models.py`
Pydantic request/response models matching the API contract in `PROJECT_SPEC.md` Section 5.1. Must be strict — no `Any` types, all fields validated.

#### `services/memory/app/hydra_client.py`
HydraDB integration layer:
```python
from hydra_db import AsyncHydraDB
import os

client = AsyncHydraDB(token=os.environ["HYDRADB_API_KEY"])

async def store_memory(tenant_id: str, content: str, metadata: dict):
    # Call client.upload.knowledge or manual memory append
    pass

async def full_recall(tenant_id: str, query: str):
    return await client.recall.full_recall(
        query=query,
        tenant_id=tenant_id,
        alpha=0.8,
        recency_bias=0
    )
```

#### Auth Middleware
```python
# All endpoints require: Authorization: Bearer <MEMORY_SERVICE_API_KEY>
# Simple string comparison against env var
# Returns 401 on missing/invalid key
# Exemption: GET /health (public)
```

### Test Plan
| Test | What it validates |
|:-----|:-----------------|
| `test_nodes.py::test_upsert_user` | User node created, returns ID |
| `test_nodes.py::test_upsert_decision_generates_embedding` | Decision node auto-embeds title+description |
| `test_nodes.py::test_reject_invalid_type` | 422 on unknown node type |
| `test_ingest.py::test_create_triple` | Triple stored, returns ID, no duplicates (UNIQUE) |
| `test_ingest.py::test_reject_orphan_triple` | 422 when subject/object node doesn't exist |
| `test_ingest.py::test_reject_invalid_predicate` | 422 on unknown predicate |
| `test_ingest.py::test_idempotent_on_replay` | Same triple twice → second returns "updated", not error |
| `test_recall.py::test_why_query` | Seeds nodes+triples, queries "Why JWT?", returns connected graph with hydrated nodes |
| `test_recall.py::test_depth_limit` | Depth=1 returns fewer triples than depth=3 |
| `test_recall.py::test_time_filter` | Old triples excluded with time range |
| `test_check.py::test_violation_detected` | Seeds decision+commit with overlapping file_paths, returns semantic violation |
| `test_check.py::test_clean_commit` | Non-overlapping file paths → status "clean" |
| `test_check.py::test_check_does_not_need_violates_triple` | /check works WITHOUT pre-existing VIOLATES triples (semantic only) |

### Gate Criteria (Phase 1A → Phase 2)
```bash
docker compose up -d memory-service
curl -s http://localhost:8000/health | jq .  # {"status":"ok","db":"connected"}
cd services/memory && python -m pytest tests/ -v  # All green
# Manual: POST a triple, then POST a recall query, verify connected result
```

---

## Phase 1B: Dify + GMI Orchestration (Infra Lead Agent)

> Runs **in parallel** with Phase 1A.

### What it builds
A self-hosted Dify instance with GMI Cloud wired as the model provider, and the chatflow DSL imported and functional.

### Steps

#### Step 1: Choose Deployment Path

**Option A — Dify Cloud (Recommended for hackathon speed):**
- Sign up at `dify.ai`, get free tier
- Import DSL via Studio → "Import DSL File"
- Skip Docker entirely for Dify layer
- URL: `https://api.dify.ai/v1` (set as `DIFY_BASE_URL`)

**Option B — Self-Hosted (Full control):**
```bash
git clone https://github.com/langgenius/dify.git /tmp/dify
cd /tmp/dify/docker
cp .env.example .env
# Edit .env: set SECRET_KEY, map to port 80 (avoid 5432/6379 conflicts)
docker compose up -d
# Access: http://localhost (Dify Web UI)
# Create admin account on first launch
```

> [!WARNING]
> If self-hosting: Dify runs its OWN Postgres (5432) + Redis (6379). Our stack also uses those ports. Fix: remap Dify's ports in its `.env` to 5433/6380, or start our stack first and let Dify detect port conflicts.

#### Step 2: Configure GMI Cloud as Model Provider

**Programmatic (preferred per IaC directive):**
```bash
# Get console auth token first:
DIFY_CONSOLE_TOKEN=$(curl -s -X POST http://localhost/console/api/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"your-password"}' | jq -r '.data.access_token')

# Add OpenAI-compatible provider:
curl -X POST http://localhost/console/api/workspaces/current/model-providers/openai_api_compatible/models \
  -H "Authorization: Bearer ${DIFY_CONSOLE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kimi-k2",
    "model_type": "llm",
    "credentials": {
      "api_key": "'${GMI_API_KEY}'",
      "endpoint_url": "'${GMI_API_BASE}'",
      "mode": "chat"
    }
  }'
```
**Fallback (if Console API doesn't support this):** Use Dify Web UI → Settings → Model Providers → Add OpenAI-compatible → Base URL: `${GMI_API_BASE}`, API Key: `${GMI_API_KEY}`, Model: `kimi-k2`.

#### Step 3: Import Chatflow DSL
```bash
# Via Dify Console API:
curl -X POST http://localhost/console/api/apps/import \
  -H "Authorization: Bearer ${DIFY_CONSOLE_TOKEN}" \
  -F "file=@production_artifacts/dify_chatflow_historian.yml"
```
If API import fails, manual import via Dify Studio → "Import DSL File" is acceptable for v1.

#### Step 4: Wire Environment Variables
In the imported chatflow, configure:
- `HYDRADB_SERVICE_URL` → `http://host.docker.internal:8000` (points to our memory-service)
- `HYDRADB_API_KEY` → from `.env`
- `GMI_API_KEY` → from `.env`

#### Step 5: Test Chatflow
Use Dify's built-in "Debug" panel:
- Input: `"Why do we use JWT instead of sessions?"`
- Expected: Chatflow executes all nodes without error (even if no data in memory yet, should return "No recorded decision found")

### Gate Criteria (Phase 1B → Phase 2)
```bash
# Dify is running
curl -s http://localhost/health | jq .

# GMI Cloud model is connected (test via Dify Studio debug)
# Chatflow imported and executable (no node errors in preview)

# Dify API is accessible for programmatic queries
curl -X POST http://localhost/v1/chat-messages \
  -H "Authorization: Bearer ${DIFY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","inputs":{},"response_mode":"blocking","user":"test"}'
```

---

## Phase 2: Ingestion Pipeline + Demo Seed (Pipeline Agent)

> **Sequential.** Depends on both Phase 1A (memory service running) and Phase 1B (Dify running).

### What it builds
Two webhook handlers (Slack + GitHub) that receive events, extract triples using GMI Cloud, and store them via the memory service. Plus a seed script for the demo.

### Detailed File Specs

#### `services/ingestion/app/slack_handler.py`
```python
# Receives Slack Events API POST:
# 1. Verify request signature (SLACK_SIGNING_SECRET)
# 2. Handle url_verification challenge
# 3. For message events:
#    a. Extract message text, user, channel, timestamp, thread_ts
#    b. Push to Redis queue: "ingestion:slack"
```

#### `services/ingestion/app/github_handler.py`
```python
# Receives GitHub Webhook POST (event: pull_request, push):
# 1. Verify HMAC signature (GITHUB_WEBHOOK_SECRET)
# 2. For PR events (opened, synchronize):
#    a. Fetch diff via GitHub API
#    b. Extract: commit SHA, file paths, author, PR number, message
#    c. Push to Redis queue: "ingestion:github"
```

#### `services/ingestion/app/extractor.py`
```python
async def extract_triples(raw_event: dict, source_type: str) -> list[Triple]:
    """
    Uses GMI Cloud (Kimi K2) to extract structured triples from raw content.
    
    Prompt engineering is critical here:
    
    SYSTEM: You are a fact extractor. Given a message/PR, extract ALL
    architectural decisions as subject-predicate-object triples.
    
    Return JSON: [{"subject": {"type": "decision", "id": "..."}, 
                    "predicate": "MADE_BY", 
                    "object": {"type": "user", "id": "..."}, 
                    "evidence": "exact quote"}]
    
    Rules:
    - Only extract DECISIONS, not opinions or questions
    - The 'id' should be a kebab-case slug of the decision
    - Include the exact quote as evidence
    """
```

> [!IMPORTANT]
> The extractor prompt is the most sensitive piece of the system. Bad extraction = garbage graph = useless recall. This needs careful prompt engineering and testing with real Slack message formats.

#### `services/ingestion/app/worker.py`
```python
# Redis consumer (async):
# 1. BLPOP from "ingestion:slack" and "ingestion:github" queues
# 2. Call extractor.extract_triples()
# 3. For each triple: POST /api/v1/nodes (upsert referenced nodes)
# 4. For each triple: POST /api/v1/ingest (store triple)
# 5. THEN: call proactive_checker.check_commit() for GitHub events
# 6. On failure: push to "ingestion:dead_letter" queue + log
# 7. Idempotency: use triple UNIQUE constraint — skip on 409 Conflict
```

#### `services/ingestion/app/proactive_checker.py`  *(NEW — fixes GAP A1)*
```python
async def check_commit(commit_sha: str, file_paths: list[str]):
    """
    Called by worker AFTER storing triples for a new commit.
    1. POST to memory-service /api/v1/check with file_paths
    2. If violations found (status == "conflict"):
       a. Format as Slack Block Kit message
       b. POST to Slack API chat.postMessage
       c. Log: violation_id, decision_id, commit_sha
    3. If clean: log and return
    
    This is the PROACTIVE path. It does NOT go through Dify.
    It calls the memory service directly and posts to Slack directly.
    """
```

#### `scripts/seed_demo.py`
Seeds the complete demo scenario for the "Ghost Review" demo. **Every node and triple is fully specified** — no placeholders:

```python
# === NODES (must be created BEFORE triples) ===

DEMO_NODES = [
    # Users
    {"type": "user", "id": "shanyu", "data": {
        "name": "Shanyu", "email": "shanyu@team.dev",
        "slack_id": "U04ABC123", "github_handle": "shanyu-d"}},
    {"type": "user", "id": "alex", "data": {
        "name": "Alex Chen", "email": "alex@team.dev",
        "slack_id": "U04DEF456", "github_handle": "alexc"}},
    
    # Decisions
    {"type": "decision", "id": "auth-jwt-over-sessions", "data": {
        "title": "Use JWT tokens instead of server-side sessions",
        "description": "JWT chosen because services A, B, C don't share a session store. Stateless auth required for microservice boundary.",
        "status": "active", "confidence": 0.95}},
    {"type": "decision", "id": "no-shared-session-store", "data": {
        "title": "No shared session store across microservices",
        "description": "Each service manages its own state. Cross-service auth via signed tokens only.",
        "status": "active", "confidence": 0.90}},
    {"type": "decision", "id": "rate-limit-at-gateway", "data": {
        "title": "Rate limiting enforced at API gateway, not per-service",
        "description": "Centralized rate limiting to avoid duplicate throttle logic across services.",
        "status": "active", "confidence": 0.85}},
    
    # Threads
    {"type": "thread", "id": "slack-arch-1710502200", "data": {
        "platform": "slack", "channel": "#architecture",
        "url": "https://team-workspace.slack.com/archives/C04ARCH/p1710502200",
        "summary": "Discussion on auth strategy for new microservice arch. Shanyu proposed JWT, team agreed."}},
    {"type": "thread", "id": "slack-arch-1710588600", "data": {
        "platform": "slack", "channel": "#architecture",
        "url": "https://team-workspace.slack.com/archives/C04ARCH/p1710588600",
        "summary": "Follow-up: confirmed no shared Redis for sessions. Each service stateless."}},
    {"type": "thread", "id": "github-pr-37", "data": {
        "platform": "github", "channel": "PR #37",
        "url": "https://github.com/team/api-gateway/pull/37",
        "summary": "PR implementing JWT auth middleware. Reviewed and merged."}},
    
    # Commits  
    {"type": "commit", "id": "commit-8a2f3b", "data": {
        "sha": "8a2f3b", "message": "feat: implement JWT auth middleware",
        "repo": "api-gateway", "file_paths": ["src/auth/jwt.ts", "src/middleware/auth.ts"],
        "pr_number": 37}},
    {"type": "commit", "id": "commit-c7d4e1", "data": {
        "sha": "c7d4e1", "message": "refactor: switch auth to express-session",
        "repo": "api-gateway", "file_paths": ["src/auth/sessions.ts", "src/auth/jwt.ts"],
        "pr_number": 42}},
    
    # Meeting
    {"type": "meeting", "id": "meeting-2026-03-14-arch-sync", "data": {
        "title": "Architecture Sync — Auth Strategy",
        "meeting_date": "2026-03-14T10:00:00Z",
        "attendees": ["shanyu", "alex"],
        "summary": "Agreed to use JWT for all inter-service auth. No shared session stores."}}
]

# === TRIPLES (15 total — forms a connected subgraph) ===

DEMO_TRIPLES = [
    # 1. JWT decision made by Shanyu
    {"subject": {"type": "decision", "id": "auth-jwt-over-sessions"},
     "predicate": "MADE_BY",
     "object": {"type": "user", "id": "shanyu"},
     "metadata": {"source": "slack_webhook", "timestamp": "2026-03-15T14:30:00Z", "confidence": 0.95}},
    
    # 2. JWT decision discussed in #architecture
    {"subject": {"type": "decision", "id": "auth-jwt-over-sessions"},
     "predicate": "DISCUSSED_IN",
     "object": {"type": "thread", "id": "slack-arch-1710502200"},
     "metadata": {"source": "slack_webhook", "timestamp": "2026-03-15T14:30:00Z", "confidence": 0.95}},
    
    # 3. JWT decision finalized in meeting
    {"subject": {"type": "decision", "id": "auth-jwt-over-sessions"},
     "predicate": "DECIDED_IN",
     "object": {"type": "meeting", "id": "meeting-2026-03-14-arch-sync"},
     "metadata": {"source": "meeting_upload", "timestamp": "2026-03-14T10:00:00Z", "confidence": 0.90}},
    
    # 4. No-shared-session decision made by Shanyu
    {"subject": {"type": "decision", "id": "no-shared-session-store"},
     "predicate": "MADE_BY",
     "object": {"type": "user", "id": "shanyu"},
     "metadata": {"source": "slack_webhook", "timestamp": "2026-03-15T15:00:00Z", "confidence": 0.90}},
    
    # 5. No-shared-session discussed in follow-up thread
    {"subject": {"type": "decision", "id": "no-shared-session-store"},
     "predicate": "DISCUSSED_IN",
     "object": {"type": "thread", "id": "slack-arch-1710588600"},
     "metadata": {"source": "slack_webhook", "timestamp": "2026-03-16T14:30:00Z", "confidence": 0.90}},
    
    # 6. Good commit RESOLVES the JWT decision
    {"subject": {"type": "commit", "id": "commit-8a2f3b"},
     "predicate": "RESOLVES",
     "object": {"type": "decision", "id": "auth-jwt-over-sessions"},
     "metadata": {"source": "github_webhook", "timestamp": "2026-03-17T09:00:00Z", "confidence": 0.92}},
    
    # 7. Good commit authored by Alex
    {"subject": {"type": "commit", "id": "commit-8a2f3b"},
     "predicate": "AUTHORED_BY",
     "object": {"type": "user", "id": "alex"},
     "metadata": {"source": "github_webhook", "timestamp": "2026-03-17T09:00:00Z", "confidence": 1.0}},
    
    # 8. Good commit reviewed by Shanyu
    {"subject": {"type": "commit", "id": "commit-8a2f3b"},
     "predicate": "REVIEWED_BY",
     "object": {"type": "user", "id": "shanyu"},
     "metadata": {"source": "github_webhook", "timestamp": "2026-03-17T11:00:00Z", "confidence": 1.0}},
    
    # 9. Good commit is constrained by JWT decision
    {"subject": {"type": "commit", "id": "commit-8a2f3b"},
     "predicate": "CONSTRAINED_BY",
     "object": {"type": "decision", "id": "auth-jwt-over-sessions"},
     "metadata": {"source": "github_webhook", "timestamp": "2026-03-17T09:00:00Z", "confidence": 0.88}},
    
    # 10. BAD commit VIOLATES the JWT decision (THE DEMO TRIGGER)
    {"subject": {"type": "commit", "id": "commit-c7d4e1"},
     "predicate": "VIOLATES",
     "object": {"type": "decision", "id": "auth-jwt-over-sessions"},
     "metadata": {"source": "github_webhook", "timestamp": "2026-03-28T10:00:00Z", "confidence": 0.91}},
    
    # 11. BAD commit also violates the no-shared-session decision
    {"subject": {"type": "commit", "id": "commit-c7d4e1"},
     "predicate": "VIOLATES",
     "object": {"type": "decision", "id": "no-shared-session-store"},
     "metadata": {"source": "github_webhook", "timestamp": "2026-03-28T10:00:00Z", "confidence": 0.87}},
    
    # 12. BAD commit authored by Alex
    {"subject": {"type": "commit", "id": "commit-c7d4e1"},
     "predicate": "AUTHORED_BY",
     "object": {"type": "user", "id": "alex"},
     "metadata": {"source": "github_webhook", "timestamp": "2026-03-28T10:00:00Z", "confidence": 1.0}},
    
    # 13. Shanyu authored the original Slack thread
    {"subject": {"type": "user", "id": "shanyu"},
     "predicate": "AUTHORED",
     "object": {"type": "thread", "id": "slack-arch-1710502200"},
     "metadata": {"source": "slack_webhook", "timestamp": "2026-03-15T14:30:00Z", "confidence": 1.0}},
    
    # 14. The PR thread references the original Slack discussion
    {"subject": {"type": "thread", "id": "github-pr-37"},
     "predicate": "REFERENCES",
     "object": {"type": "thread", "id": "slack-arch-1710502200"},
     "metadata": {"source": "github_webhook", "timestamp": "2026-03-17T09:00:00Z", "confidence": 0.85}},
    
    # 15. Rate limit decision made by Alex (unrelated — tests graph isolation)
    {"subject": {"type": "decision", "id": "rate-limit-at-gateway"},
     "predicate": "MADE_BY",
     "object": {"type": "user", "id": "alex"},
     "metadata": {"source": "slack_webhook", "timestamp": "2026-03-20T11:00:00Z", "confidence": 0.85}}
]
```

**Why these specific triples matter for the demo:**
- Triples 1-3 create the decision trail that the "Why JWT?" query traverses
- Triples 6-9 show a "good" commit that aligns with the decision
- Triples 10-12 are the **violation** that the proactive check detects
- Triple 14 connects the GitHub PR back to the original Slack thread (deep citation)
- Triple 15 proves the graph doesn't over-recall (unrelated decisions stay isolated)

### Gate Criteria (Phase 2 → Phase 3)
```bash
# Seed demo data (creates nodes with embeddings, then triples)
python scripts/seed_demo.py

# Verify data in memory service (FIX GAP-15: include auth header)
curl -s http://localhost:8000/api/v1/recall \
  -H "Authorization: Bearer ${MEMORY_SERVICE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"query":"Why JWT?","scope":{"types":["decision"],"depth":2}}' | jq .
# Should return the JWT decision with Shanyu as maker and the Slack thread

# Verify constraint check (FIX GAP-16: file_paths as array)
curl -s http://localhost:8000/api/v1/check \
  -H "Authorization: Bearer ${MEMORY_SERVICE_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"code_diff":"- import jwt\n+ import session_store","file_paths":["src/auth/handler.ts"]}' | jq .
# Should return: {"status":"conflict","violations":[...]}
```

> [!IMPORTANT]
> **GAP-17 fix:** The `seed_demo.py` script MUST call the embedding service for every Decision, Thread, and Commit node's text content when creating nodes via `/api/v1/nodes`. The `/nodes` endpoint handles this automatically — it calls `embed_text()` on relevant fields. If the embedding service is down during seeding, the seed will fail explicitly (503) rather than creating nodes with NULL embeddings that silently break vector search.

---

## Phase 3: Delivery + End-to-End (Integration Agent)

> **Sequential.** The final assembly. This is where the demo comes alive.

### What it builds
The Slack bot that:
1. Listens for messages mentioning the bot
2. Routes to Dify chatflow
3. Returns the answer in-thread

Plus the "proactive alert" path:
1. GitHub webhook fires on PR
2. Ingestion → extraction → memory service check
3. If violation detected → Slack alert via bot

### Detailed File Specs

#### `services/delivery/app/slack_bot.py`
```python
# Two modes:

# MODE 1: Reactive (user asks "Why?")
# 1. Slack Events API → bot mention detected
# 2. Extract query text
# 3. POST to Dify API: /v1/chat-messages
#    (Dify handles: intent extraction → HydraDB recall → GMI synthesis)
# 4. Post Dify response back to Slack thread

# MODE 2: Proactive (PR triggers alert)
# 1. GitHub webhook → ingestion → memory check → violation found
# 2. Format violation as Slack Block Kit message
# 3. POST to Slack API: chat.postMessage to #engineering channel
# 4. Include: decision title, author, date, thread link, recommendation
```

### End-to-End Test Script
```bash
#!/bin/bash
# === E2E Test: The Ghost Review Demo ===

# Step 1: Verify all services up
echo "Checking services..."
curl -sf http://localhost:8000/health || exit 1  # memory
curl -sf http://localhost:8001/health || exit 1  # ingestion
curl -sf http://localhost/health || exit 1       # dify

# Step 2: Seed demo data (idempotent)
python scripts/seed_demo.py

# Step 3: Test "Why?" query through Dify
RESPONSE=$(curl -s -X POST http://localhost/v1/chat-messages \
  -H "Authorization: Bearer ${DIFY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Why do we use JWT instead of sessions?",
    "inputs": {"file_context": ""},
    "response_mode": "blocking",
    "user": "e2e-test"
  }')
echo "Why query response:"
echo "$RESPONSE" | jq -r '.answer'
# MUST contain: "shanyu", "March 15", "JWT", "microservice"

# Step 4: Test constraint check through Dify
RESPONSE=$(curl -s -X POST http://localhost/v1/chat-messages \
  -H "Authorization: Bearer ${DIFY_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Check this code change for conflicts",
    "inputs": {"file_context": "- import { signJWT } from ./auth/jwt\n+ import { createSession } from ./auth/sessions"},
    "response_mode": "blocking",
    "user": "e2e-test"
  }')
echo "Check response:"
echo "$RESPONSE" | jq -r '.answer'
# MUST contain: "CONSTRAINT CONFLICT" or "violation"

echo "=== E2E PASS ==="
```

### Gate Criteria (Phase 3 → Phase 4)
- [ ] "Why?" query returns answer citing Shanyu, date, Slack thread
- [ ] Constraint check returns violation with evidence
- [ ] Slack bot posts answer in correct thread
- [ ] Proactive alert appears in `#engineering` channel on simulated PR

---

## Phase 4: Demo Polish (Demo Agent)

### Demo Script: "The Ghost Review" (90 seconds)

| Time | Action | What's Shown |
|:-----|:-------|:-------------|
| 0:00 | Narration | "Most engineering teams suffer from Architectural Amnesia..." |
| 0:10 | Show Slack | A real Slack thread from "2 weeks ago" — JWT decision |
| 0:25 | Show GitHub | A PR that switches from JWT to sessions |
| 0:35 | Show Slack | ⚠️ Alert appears: "CONSTRAINT CONFLICT — PR #42" |
| 0:50 | Type in Slack | "@historian Why do we use JWT instead of sessions?" |
| 1:00 | Show response | Full decision trail with person, date, thread link |
| 1:15 | Show graph | (Optional) Mermaid diagram of the decision graph |
| 1:25 | End card | "ContextCortex — Memory that ships." |

---

## Risk Mitigation Matrix

| # | Risk | Probability | Impact | Mitigation |
|:--|:-----|:-----------|:-------|:-----------|
| 1 | HydraDB SDK undocumented or broken | Medium | High | `MemoryBackend` protocol pattern — swap to Postgres silently |
| 2 | GMI Cloud rate limits during demo | Low | Critical | Cache demo queries in Redis; pre-warm the model |
| 3 | Dify DSL import version mismatch | Medium | Medium | Manual import as fallback; pin Dify version in compose |
| 4 | Triple extraction quality is low | High | High | Hand-tune prompt with 10+ real Slack examples; add confidence threshold (>0.7) |
| 5 | Slack webhook setup requires public URL | High | Medium | Use `ngrok` for development; document in README |
| 6 | Docker port conflicts (Dify vs. our services) | Medium | Low | Explicit port mapping: Dify=80, memory=8000, ingestion=8001 |

---

## Environment Variable Checklist

Before any agent executes, user must create `.env` with:

| Variable | Required By Phase | How To Get |
|:---------|:-----------------|:-----------|
| `GMI_API_KEY` | 1A (embeddings), 1B (Dify) | GMI Cloud dashboard |
| `GMI_API_BASE` | 1A, 1B | GMI Cloud dashboard |
| `HYDRADB_API_KEY` | 1A (if using HydraDB backend) | HydraDB dashboard |
| `HYDRADB_BASE_URL` | 1A | HydraDB dashboard |
| `SLACK_BOT_TOKEN` | 3 | Slack App → OAuth Tokens |
| `SLACK_SIGNING_SECRET` | 2 (webhook verification) | Slack App → Basic Info |
| `SLACK_CHANNEL_ID` | 3 | Right-click channel → Copy ID |
| `GITHUB_WEBHOOK_SECRET` | 2 | GitHub repo → Settings → Webhooks |
| `DIFY_API_KEY` | 3 (E2E) | Dify Studio → API Access |
| `DATABASE_URL` | 1A | Auto from docker-compose |
| `REDIS_URL` | 2 | Auto from docker-compose |
