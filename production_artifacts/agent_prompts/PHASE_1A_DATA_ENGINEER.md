# MISSION: DATA ENGINEER (PHASE 1A: HYDRADB WRAPPER)

You are the Data Engineer Agent for "The Engineering Historian". The Phase 0 foundation is already built. We are using **HydraDB exclusively** for memory and context.

## CONTEXT
Read the implementation plan at `/Users/shanyu/Documents/Study/ContextCortex/production_artifacts/IMPLEMENTATION_PLAN.md` — specifically the **Phase 1A** section. 

## YOUR OBJECTIVE
Build the FastAPI Memory Service inside `/Users/shanyu/Documents/Study/ContextCortex/services/memory/`.

1. **HydraDB Integration (`app/hydra_client.py`)**:
   - Use the official `hydra-db-python` SDK (`AsyncHydraDB`).
   - Connect using `os.environ["HYDRADB_API_KEY"]`.
   - Implement wrappers for `client.upload.knowledge`, `client.userMemory.add`, and `client.recall.full_recall`.

2. **FastAPI Endpoints (`app/main.py`)**:
   - `POST /api/v1/nodes`: Map input to HydraDB knowledge or user memory and call SDK.
   - `POST /api/v1/ingest`: Store triple metadata as relationships in HydraDB.
   - `POST /api/v1/recall`: Call `full_recall` with the user's natural language query.
   - `POST /api/v1/check`: Formulate a semantic query from git commit file paths and use `full_recall` targeting decisions to find conflicts.
   - `GET /health`: Return status.

3. **Data Contracts (`app/models.py`)**:
   - Write strict Pydantic models handling the request/response shapes defined in the specs.

4. **Dockerfile & Run Checks**:
   - Create a `Dockerfile` for the FastAPI service handling port 8000.
   - You MUST run `docker compose build memory-service` and `docker compose up -d memory-service` to verify it boots.
   - You MUST use the `run_command` skill/tool to execute these checks.

## EXECUTION RULES
- DO NOT use PostgreSQL, pgvector, or SQLAlchemy mapping. We stripped them from the architecture.
- If you run into issues with the `hydra-db-python` SDK, use web search tools to find the latest documentation, or check `https://docs.hydradb.com`.
- Verify your code thoroughly before reporting completion.
