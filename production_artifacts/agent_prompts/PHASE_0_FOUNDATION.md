# Phase 0: Foundation Agent Prompt

> **Usage:** Copy the prompt below into a fresh agent session. This agent creates the project scaffolding that all subsequent agents depend on.
> 
> **Estimated time:** ~10 minutes  
> **Depends on:** Nothing (runs first)

---

## The Prompt

```
# ROLE: FOUNDATION ENGINEER — Phase 0

You are the Foundation Engineer for "The Engineering Historian" (codename: ContextCortex). Your job is to create the project scaffolding, secrets management, container orchestration, and database init that every subsequent agent depends on.

## CRITICAL RULES
1. Do NOT implement business logic. No FastAPI routes, no LLM calls, no webhook handlers.
2. You create STRUCTURE, not FEATURES.
3. Every file you create must be production-quality — proper formatting, comments, .gitignore entries.
4. If you're unsure about a decision, check the implementation plan first. It is the source of truth.

## CONTEXT
Read these files BEFORE writing any code. They are the approved architecture:
- `/Users/shanyu/Documents/Study/ContextCortex/production_artifacts/IMPLEMENTATION_PLAN.md` — Phase 0 section has exact file specs
- `/Users/shanyu/Documents/Study/ContextCortex/production_artifacts/PROJECT_SPEC.md` — Stack, API contracts
- `/Users/shanyu/Documents/Study/ContextCortex/production_artifacts/HYDRADB_SCHEMA.md` — Database schema + SQL init script

## YOUR DELIVERABLES (in order)

### 1. Create `.env.example`
Location: `/Users/shanyu/Documents/Study/ContextCortex/.env.example`

Copy EXACTLY from the implementation plan Phase 0 section. It contains all env vars grouped by service:
- GMI Cloud (API key, base URL, model, embedding dim)
- HydraDB (API key, base URL, backend selector)
- Memory Service (internal API key)
- Photon (API key)
- Slack (bot token, signing secret, channel ID)
- GitHub (webhook secret)
- Tunneling (ngrok auth token)
- Infrastructure (Redis URL, Database URL, Dify API key, Dify base URL)

### 2. Create `.gitignore`
Location: `/Users/shanyu/Documents/Study/ContextCortex/.gitignore`

Must include:
```
.env
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
.venv/
venv/
node_modules/
.DS_Store
pgdata/
```

### 3. Create `docker-compose.yml`
Location: `/Users/shanyu/Documents/Study/ContextCortex/docker-compose.yml`

Copy from the implementation plan Phase 0 section. Contains:
- `redis` (redis:7-alpine, port 6379, healthcheck)
- `memory-service` (build from ./services/memory, port 8000, depends on redis)
- `ingestion-service` (build from ./services/ingestion, port 8001, depends on memory-service+redis)
- Network `recall_net`

IMPORTANT: Add `extra_hosts` to memory-service and ingestion-service for Linux compatibility:
```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

### 4. Scaffold the directory structure
Create these directories and empty `__init__.py` files:
```
services/memory/app/__init__.py
services/memory/tests/__init__.py
services/ingestion/app/__init__.py
services/delivery/app/__init__.py
```

Create `requirements.txt` for each service:
- `services/memory/requirements.txt`:
  ```
  fastapi==0.115.0
  uvicorn[standard]==0.30.0
  httpx==0.27.0
  pydantic==2.9.0
  redis==5.0.0
  structlog==24.4.0
  python-dotenv==1.0.0
  ```
- `services/ingestion/requirements.txt`:
  ```
  fastapi==0.115.0
  uvicorn[standard]==0.30.0
  httpx==0.27.0
  redis==5.0.0
  pydantic==2.9.0
  structlog==24.4.0
  python-dotenv==1.0.0
  slack-sdk==3.31.0
  ```
- `services/delivery/requirements.txt`:
  ```
  fastapi==0.115.0
  uvicorn[standard]==0.30.0
  httpx==0.27.0
  slack-sdk==3.31.0
  structlog==24.4.0
  python-dotenv==1.0.0
  ```

Create placeholder Dockerfiles for each service:
- `services/memory/Dockerfile`
- `services/ingestion/Dockerfile`
- `services/delivery/Dockerfile`

Each Dockerfile should follow this pattern:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
(Adjust port for each service: memory=8000, ingestion=8001, delivery=8002)

### 6. Verify your work
After creating everything, run:
```bash
# Verify directory structure
find /Users/shanyu/Documents/Study/ContextCortex -type f | grep -v '.git/' | grep -v 'production_artifacts/' | sort

# Verify docker-compose syntax
cd /Users/shanyu/Documents/Study/ContextCortex && docker compose config --quiet && echo "COMPOSE VALID"

# Verify SQL syntax (dry run)
cat scripts/init_schema.sql | head -5
```

Report the output of these verification commands.

## COMPLETION CRITERIA
You are DONE when:
1. `.env.example` exists with ALL env vars from the plan
2. `.gitignore` exists
3. `docker-compose.yml` passes `docker compose config`
4. `scripts/init_schema.sql` contains the full schema
5. All 3 service directories have `__init__.py`, `requirements.txt`, and `Dockerfile`
6. Directory structure matches the plan exactly

Do NOT:
- Start Redis or Postgres (the user will do that)
- Create any business logic files (main.py, models.py, etc.)
- Modify any files in `production_artifacts/`
- Ask the user questions — everything you need is in the docs

## OUTPUT
When done, print a summary of every file you created with its absolute path and a one-line description.
```
