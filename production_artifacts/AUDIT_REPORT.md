# 🔍 Critical Audit Report: The Engineering Historian

> **Auditor:** Self (Principal Engineer mode)  
> **Date:** 2026-03-28  
> **Verdict:** Plan is strong structurally but has 18 gaps that would cause failures during execution.

---

## Category A: Architectural Loopholes (Would Break the Demo)

### GAP A1: Proactive Check Flow is Disconnected
**Severity:** 🔴 CRITICAL  
**Location:** Implementation Plan Phase 3 + Dify DSL

**Problem:** The Dify chatflow handles "Why?" queries and manual "Check" queries through user input. But the **proactive alert** (GitHub PR → auto-detect violation → Slack alert) completely **bypasses Dify**. There's no path defined for:
```
GitHub webhook → ingestion service → ??? → memory service /check → Slack alert
```
The implementation plan says "ingestion → extraction → memory service check → Slack alert" but the ingestion worker (`worker.py`) is only designed to extract triples and store them. It doesn't call `/check`. And even if it did, who formats the violation and posts to Slack?

**Fix:**  
The proactive path needs its own flow, separate from Dify:
```
GitHub webhook → ingestion worker extracts triples + stores them
  → THEN: worker calls POST /api/v1/check with the new commit's file_paths
  → If violations found: worker calls Slack API directly (or via delivery service)
```
Add a `proactive_checker.py` to the ingestion service that runs after triple storage.

---

### GAP A2: Two Docker Compose Stacks = Networking Nightmare
**Severity:** 🟡 HIGH  
**Location:** Implementation Plan Phase 1B

**Problem:** Dify runs its own `docker compose` (from the cloned Dify repo) with its own Postgres, Redis, and internal network. Our `docker-compose.yml` runs a separate stack with our Postgres, Redis, and memory-service. These are on **different Docker networks**. The Dify chatflow's HTTP Request node needs to reach `memory-service:8000`, but it can't because they're on different networks.

**Fix options:**
1. **Option A (Recommended):** Use `host.docker.internal:8000` as the URL in Dify's HTTP nodes. Works on macOS Docker Desktop.
2. **Option B:** Add our `recall_net` as an external network in Dify's compose, and connect Dify's API container to it.
3. **Option C:** Run everything in one unified compose file (fragile, not recommended).

Document Option A as the default, Option B as the production path.

---

### GAP A3: The "General" Query Path Goes Nowhere
**Severity:** 🟡 HIGH  
**Location:** Dify DSL — Query Router

**Problem:** The intent extractor classifies 3 types: `why_query`, `constraint_check`, `general`. But the IF/ELSE router only has a true branch (why_query) and a false branch (everything else → check). If someone asks "What decisions have been made this week?" — it gets routed to the constraint check path, which expects a code diff. It will fail.

**Fix:**  
Replace the single IF/ELSE with a **Question Classifier** node (Dify native) that has 3 branches:
- Class 1: "Why?" query → Recall path
- Class 2: Constraint check → Check path  
- Class 3: General → New LLM node that queries HydraDB with broad scope and summarizes

Or simpler: Use two IF/ELSE nodes in sequence:
```
IF contains "why_query" → recall path
ELIF contains "constraint_check" → check path
ELSE → fallback LLM that does broad recall
```

---

## Category B: Data Integrity Issues

### GAP B1: SQL Query Pattern #1 Has Broken Join Logic  
**Severity:** 🔴 CRITICAL  
**Location:** HYDRADB_SCHEMA.md, Query Pattern 1

**Problem:** The "Why was X built this way?" query searches for triples where `predicate = 'CONSTRAINED_BY'` and then checks if the object is a commit touching certain files. But `CONSTRAINED_BY` is defined as `Commit → Decision` (subject=commit, object=decision). The query has the join direction inverted. Also, it's searching for commits that constrain decisions, when it should be finding decisions that constrain commits touching those file paths.

**Fix:**
```sql
-- CORRECT: Find decisions that constrain commits touching a file path
SELECT d.title, d.description, t.url, t.channel, u.name
FROM commits c
JOIN triples t1 ON t1.subject_id = c.id AND t1.subject_type = 'commit'
  AND t1.predicate = 'CONSTRAINED_BY'
JOIN decisions d ON t1.object_id = d.id AND t1.object_type = 'decision'
LEFT JOIN triples t2 ON t2.subject_id = d.id AND t2.predicate = 'DISCUSSED_IN'
LEFT JOIN threads t ON t2.object_id = t.id
LEFT JOIN triples t3 ON t3.subject_id = d.id AND t3.predicate = 'MADE_BY'
LEFT JOIN users u ON t3.object_id = u.id
WHERE 'src/auth/jwt.ts' = ANY(c.file_paths)
  AND d.status = 'active';
```

---

### GAP B2: No Referential Integrity on Triples Table
**Severity:** 🟡 HIGH  
**Location:** HYDRADB_SCHEMA.md, Schema Init Script

**Problem:** The triples table has `subject_id` and `object_id` as TEXT fields with no foreign key constraints. You can create a triple pointing to a non-existent node. During the demo, a bad seed could create orphan triples that cause null results in joins.

**Fix:** We can't use standard FKs because subject_id/object_id point to different tables depending on the type. Add application-level validation in the memory service's `/ingest` endpoint:
```python
# Before storing triple, verify both subject and object nodes exist
subject_exists = await verify_node_exists(triple.subject_type, triple.subject_id)
object_exists = await verify_node_exists(triple.object_type, triple.object_id)
if not (subject_exists and object_exists):
    raise HTTPException(422, "Subject or object node does not exist. Upsert nodes first.")
```
Also add a `POST /api/v1/nodes` endpoint for upserting nodes. Currently the API contract only has triple operations — there's no way to create User/Thread/Decision nodes directly.

---

### GAP B3: `TIMESTAMP` Triple in Spec Doesn't Match Schema
**Severity:** 🟢 LOW  
**Location:** PROJECT_SPEC.md Section 3.1

**Problem:** The triple model example shows:
```
(Decision:auth_jwt_over_sessions) -[TIMESTAMP]-> (2026-03-15T14:30:00Z)
```
But `TIMESTAMP` is not a valid predicate in the schema. Timestamps are stored as `extracted_at` on the EdgeMetadata and `created_at` on nodes.

**Fix:** Remove the `TIMESTAMP` triple from the spec example. It's metadata, not a relationship.

---

### GAP B4: Embedding Dimension Ambiguity
**Severity:** 🟡 HIGH  
**Location:** HYDRADB_SCHEMA.md + embeddings.py spec

**Problem:** Schema hardcodes `vector(768)` but the plan says "GMI Cloud embedding endpoint" without specifying which model or confirming the dimension. If GMI uses a different embedding model (e.g., 1024-dim or 1536-dim), the schema breaks with a dimension mismatch error.

**Fix:** 
1. Make embedding dimension configurable: `EMBEDDING_DIM=768` in `.env`
2. The schema init script should use a variable: `embedding vector(${EMBEDDING_DIM})`
3. Document fallback: if GMI doesn't offer embeddings, use OpenAI's `text-embedding-3-small` (1536-dim) or sentence-transformers locally (768-dim)

---

## Category C: Missing Specifications

### GAP C1: No Error Handling in Dify Chatflow
**Severity:** 🟡 HIGH  
**Location:** Dify DSL

**Problem:** If the HydraDB HTTP request fails (timeout, 500, service down), the chatflow crashes. There's no fallback Answer node that says "Sorry, I couldn't reach the memory service."

**Fix:** Add an IF/ELSE after each HTTP node checking the status code:
```yaml
- If status_code == 200 → proceed to LLM synthesis
- Else → Answer node: "⚠️ Memory service unavailable. Please try again."
```

---

### GAP C2: No Authentication on Memory Service Endpoints
**Severity:** 🟡 HIGH  
**Location:** Implementation Plan Phase 1A

**Problem:** The memory service API endpoints have no auth. Anyone on the Docker network (or localhost) can write arbitrary triples. During hackathon demo this is fine, but if Dify sends `Authorization: Bearer` headers, the service needs to accept and validate them.

**Fix:** Add a simple API key middleware:
```python
# Bearer token validation — checks against MEMORY_SERVICE_API_KEY env var
# For demo: simple string comparison
# For production: JWT validation
```

---

### GAP C3: No Logging/Observability Strategy
**Severity:** 🟢 LOW  
**Location:** All services

**Problem:** No mention of structured logging anywhere. When the demo fails (and it will during dev), there's no way to trace what happened.

**Fix:** Add to implementation plan:
- All services use Python `structlog` with JSON output
- Log format: `{"timestamp", "service", "event", "triple_id", "latency_ms"}`
- Docker compose: add `logging.driver: json-file` with size limits

---

### GAP C4: No Node Upsert Endpoint
**Severity:** 🔴 CRITICAL  
**Location:** PROJECT_SPEC.md Section 5.1 + Implementation Plan

**Problem:** The API contract only defines `/ingest` (triples), `/recall`, and `/check`. But there's no endpoint to create the **nodes** (Users, Decisions, Threads, Commits) that triples reference. The seed script needs to insert nodes before triples. The ingestion worker needs to create User/Thread/Commit nodes dynamically.

**Fix:** Add to API contract:
```yaml
# POST /api/v1/nodes — Upsert a node
Request:
  type: "user" | "decision" | "thread" | "commit" | "meeting"
  id: string
  data: { ... }  # Fields matching the node type schema
Response:
  node_id: string
  status: "created" | "updated"
```

---

### GAP C5: `file_path` Field in /check Request is Singular
**Severity:** 🟢 LOW  
**Location:** PROJECT_SPEC.md Section 5.1

**Problem:** `/check` takes a single `file_path: string` but PRs typically touch multiple files. A constraint might only apply to one of them.

**Fix:** Change to `file_paths: [string]` (array).

---

## Category D: Implementation Plan Blind Spots

### GAP D1: Seed Script Incomplete — Only Shows 2 of 15 Triples
**Severity:** 🟡 HIGH  
**Location:** Implementation Plan Phase 2

**Problem:** The seed script shows the skeleton but only 2 concrete triples. The remaining 13 are described vaguely. An execution agent will have to guess the rest, and they'll likely miss critical relationships needed for the demo.

**Fix:** Fully specify all 15 triples with exact IDs, plus all node data. All triples must form a connected subgraph that the "Why JWT?" query can traverse completely to produce the expected demo output.

---

### GAP D2: No ngrok or Tunnel in Docker Compose
**Severity:** 🟡 HIGH  
**Location:** Implementation Plan Phase 2

**Problem:** Slack/GitHub webhooks need a public URL. The plan mentions ngrok in the risk matrix but doesn't include it in the compose file or setup steps.

**Fix:** Add ngrok to docker-compose or provide explicit setup instructions:
```yaml
  tunnel:
    image: ngrok/ngrok:latest
    command: http ingestion-service:8001
    env: NGROK_AUTHTOKEN=${NGROK_AUTHTOKEN}
    ports: ["4040:4040"]  # Inspection UI
```
Add `NGROK_AUTHTOKEN` to `.env.example`.

---

### GAP D3: No Dify Cloud Alternative
**Severity:** 🟢 LOW  
**Location:** Implementation Plan Phase 1B

**Problem:** Self-hosting Dify adds complexity (separate Docker Compose, own DB, port conflicts). For a hackathon, Dify Cloud (free tier) might be faster.

**Fix:** Document both paths:
- **Path A (recommended for hackathon):** Use Dify Cloud (dify.ai) — import DSL via Web UI, configure GMI as model provider. Zero infra overhead.
- **Path B (production):** Self-hosted Dify with Docker.

---

### GAP D4: No Data Flow Diagram for the Proactive Path
**Severity:** 🟡 HIGH  
**Location:** Implementation Plan

**Problem:** The "Why?" path has a clear diagram (through Dify). The proactive path (GitHub webhook → alert) has no diagram. It's described in prose across Phase 2 and Phase 3 but the exact service-to-service flow is ambiguous.

**Fix:** Add explicit sequence diagram:
```
GitHub PR → (webhook) → ingestion-service/github_handler
  → (Redis queue) → ingestion-service/worker
    → (GMI extract triples) → memory-service/POST /ingest
    → (then) → memory-service/POST /check  
    → (if violations) → delivery-service/slack_bot → Slack API
```

---

### GAP D5: Phase 1B Step 2 Says "Via Web UI" — Violates IaC Directive
**Severity:** 🟡 HIGH  
**Location:** Implementation Plan Phase 1B, Step 2

**Problem:** The user's original directive says "Do not instruct the user to click in UIs. Generate... code that I can import/run." But Phase 1B Step 2 says "Via Dify Web UI → Settings → Model Providers" — this is a click-in-UI instruction.

**Fix:** Use Dify's Console API or environment variables to configure the model provider programmatically:
```bash
# Dify stores model provider configs in its DB.
# Use the Console API to add the provider:
curl -X POST http://localhost/console/api/workspaces/current/model-providers \
  -H "Authorization: Bearer ${DIFY_CONSOLE_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai_api_compatible",
    "credentials": {
      "api_key": "${GMI_API_KEY}",
      "endpoint_url": "https://api.gmicloud.ai/v1"
    }
  }'
```
If the Console API doesn't support this, document it as a known manual step with exact click path.

---

## Summary: Fix Priority

| Priority | Count | Gaps |
|:---------|:------|:-----|
| 🔴 CRITICAL (blocks demo) | 3 | A1, B1, C4 |
| 🟡 HIGH (causes pain) | 9 | A2, A3, B2, B4, C1, C2, D1, D2, D4, D5 |
| 🟢 LOW (nice to have) | 4 | B3, C3, C5, D3 |

**Next step:** Apply all CRITICAL and HIGH fixes to the production artifacts.
