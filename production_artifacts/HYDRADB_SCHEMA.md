# HydraDB Graph Schema: The Engineering Historian

## Overview
This schema models **engineering decisions as a knowledge graph** using HydraDB's Cortex triple store. Every node is an entity, every edge is a typed relationship with metadata.

---

## Node Types

### `User`
Represents a team member who makes decisions and writes code.
```yaml
User:
  id: string          # e.g., "user:shanyu"
  name: string
  email: string
  slack_id: string    # For Photon routing
  github_handle: string
  created_at: datetime
```

### `Decision`
The atomic unit of memory. A specific architectural or design choice.
```yaml
Decision:
  id: string          # e.g., "decision:auth_jwt_over_sessions"
  title: string       # Human-readable summary
  description: string # Full context
  status: enum        # "active" | "superseded" | "reverted"
  confidence: float   # 0.0–1.0, extraction confidence
  created_at: datetime
  embedding: vector   # 768-dim for hybrid search
```

### `Thread`
A Slack thread or GitHub discussion where context lives.
```yaml
Thread:
  id: string          # e.g., "thread:slack_C04A2B3_1711200000"
  platform: enum      # "slack" | "github" | "meeting"
  channel: string     # "#architecture", "PR #42"
  url: string         # Deep link
  summary: string     # GMI-extracted summary
  created_at: datetime
  embedding: vector
```

### `Commit`
A Git commit or PR that implements or violates a decision.
```yaml
Commit:
  id: string          # e.g., "commit:8a2f3b"
  sha: string
  message: string
  repo: string
  file_paths: [string]
  pr_number: int?
  created_at: datetime
  embedding: vector
```

### `Meeting`
A meeting or sync where decisions were discussed.
```yaml
Meeting:
  id: string          # e.g., "meeting:2026-03-15-arch-sync"
  title: string
  date: datetime
  attendees: [string] # User IDs
  transcript_url: string?
  summary: string
  embedding: vector
```

---

## Edge Types (Predicates)

| Predicate | Subject → Object | Description |
|:----------|:-----------------|:------------|
| `MADE_BY` | Decision → User | Who made the decision |
| `DISCUSSED_IN` | Decision → Thread | Where it was discussed |
| `DECIDED_IN` | Decision → Meeting | Meeting where it was finalized |
| `RESOLVES` | Commit → Decision | Code that implements a decision |
| `VIOLATES` | Commit → Decision | Code that conflicts with a decision |
| `SUPERSEDES` | Decision → Decision | A newer decision replacing an older one |
| `AUTHORED` | User → Thread | Who wrote in a thread |
| `AUTHORED_BY` | Commit → User | Who wrote the commit |
| `REVIEWED_BY` | Commit → User | Who reviewed the PR |
| `REFERENCES` | Thread → Thread | Cross-thread references |
| `CONSTRAINED_BY` | Commit → Decision | Code constrained by a prior decision |

---

## Edge Metadata
Every edge carries:
```yaml
EdgeMetadata:
  triple_id: string     # Unique ID for the triple
  confidence: float     # 0.0–1.0, extraction confidence
  source: enum          # "slack_webhook" | "github_webhook" | "meeting_upload" | "manual"
  extracted_at: datetime
  raw_evidence: string  # The exact quote that justifies this triple
```

---

## Schema Init Script (PostgreSQL + pgvector)

Since HydraDB's Cortex layer doesn't have public docs, we abstract the graph as relational tables for portability.

> **Embedding Dimension:** Default `768` (sentence-transformers). Set `EMBEDDING_DIM` env var if your embedding model uses a different dimension (e.g., 1536 for OpenAI, 1024 for some GMI models). The init script uses this value.

> **Node Validation:** The triples table uses polymorpic foreign keys (subject/object can reference any node table). Referential integrity is enforced at the **application layer**, not the DB. The memory service's `/ingest` endpoint MUST verify that both subject and object nodes exist before storing a triple.

```sql
-- ============================================================
-- ContextCortex: Graph Schema (PostgreSQL Implementation)
-- Portable: Works with HydraDB Cortex or plain Postgres
-- ============================================================

-- ENUM types
CREATE TYPE node_type AS ENUM ('user', 'decision', 'thread', 'commit', 'meeting');
CREATE TYPE predicate_type AS ENUM (
  'MADE_BY', 'DISCUSSED_IN', 'DECIDED_IN', 'RESOLVES',
  'VIOLATES', 'SUPERSEDES', 'AUTHORED', 'AUTHORED_BY',
  'REVIEWED_BY', 'REFERENCES', 'CONSTRAINED_BY'
);
CREATE TYPE decision_status AS ENUM ('active', 'superseded', 'reverted');
CREATE TYPE source_type AS ENUM ('slack_webhook', 'github_webhook', 'meeting_upload', 'manual');

-- Enable vector extension for hybrid search
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================
-- NODE TABLES
-- ============================================================

CREATE TABLE users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT UNIQUE,
  slack_id TEXT,
  github_handle TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE decisions (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT,
  status decision_status DEFAULT 'active',
  confidence FLOAT DEFAULT 1.0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  embedding vector(768)
);

CREATE TABLE threads (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL,         -- 'slack', 'github', 'meeting'
  channel TEXT,
  url TEXT,
  summary TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  embedding vector(768)
);

CREATE TABLE commits (
  id TEXT PRIMARY KEY,
  sha TEXT NOT NULL UNIQUE,
  message TEXT,
  repo TEXT NOT NULL,
  file_paths TEXT[],
  pr_number INT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  embedding vector(768)
);

CREATE TABLE meetings (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  meeting_date TIMESTAMPTZ,
  attendees TEXT[],               -- Array of user IDs
  transcript_url TEXT,
  summary TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  embedding vector(768)
);

-- ============================================================
-- TRIPLE TABLE (The Core Graph)
-- ============================================================

CREATE TABLE triples (
  id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  subject_type node_type NOT NULL,
  subject_id TEXT NOT NULL,
  predicate predicate_type NOT NULL,
  object_type node_type NOT NULL,
  object_id TEXT NOT NULL,
  confidence FLOAT DEFAULT 1.0,
  source source_type NOT NULL,
  raw_evidence TEXT,
  extracted_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Prevent duplicate triples
  UNIQUE (subject_type, subject_id, predicate, object_type, object_id)
);

-- ============================================================
-- INDEXES (Performance-Critical)
-- ============================================================

-- Triple lookups by subject (forward traversal)
CREATE INDEX idx_triples_subject ON triples (subject_type, subject_id);

-- Triple lookups by object (reverse traversal)
CREATE INDEX idx_triples_object ON triples (object_type, object_id);

-- Predicate filtering
CREATE INDEX idx_triples_predicate ON triples (predicate);

-- Time-range queries
CREATE INDEX idx_triples_extracted ON triples (extracted_at);
CREATE INDEX idx_decisions_created ON decisions (created_at);

-- Vector similarity search (HNSW for speed)
CREATE INDEX idx_decisions_embedding ON decisions USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_threads_embedding ON threads USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_commits_embedding ON commits USING hnsw (embedding vector_cosine_ops);
```

---

## Query Patterns

### 1. "Why was X built this way?"
```sql
-- Given a file path, find all decisions that constrain commits touching it,
-- plus who made the decision and where it was discussed.
SELECT d.title, d.description, t.url, t.channel, u.name AS decided_by,
       tr1.raw_evidence, tr1.confidence, d.created_at
FROM commits c
JOIN triples tr1 ON tr1.subject_id = c.id 
  AND tr1.subject_type = 'commit'
  AND tr1.predicate IN ('CONSTRAINED_BY', 'RESOLVES')
JOIN decisions d ON tr1.object_id = d.id 
  AND tr1.object_type = 'decision'
  AND d.status = 'active'
LEFT JOIN triples tr2 ON tr2.subject_id = d.id 
  AND tr2.predicate = 'DISCUSSED_IN'
LEFT JOIN threads t ON tr2.object_id = t.id
LEFT JOIN triples tr3 ON tr3.subject_id = d.id 
  AND tr3.predicate = 'MADE_BY'
LEFT JOIN users u ON tr3.object_id = u.id
WHERE $1 = ANY(c.file_paths);  -- $1 = 'src/auth/jwt.ts'
```

### 2. Proactive Constraint Check (Semantic — GAP-12 fix)
```sql
-- Given file_paths from a new PR, find active decisions that CONSTRAIN those paths.
-- This does NOT require pre-existing VIOLATES triples — it finds constraints
-- via existing commits that touch the same files, then scores semantically.
--
-- Step 1: Find decisions related to the affected file paths
WITH related_decisions AS (
  SELECT DISTINCT d.id, d.title, d.description, d.embedding,
         tr.raw_evidence, tr.confidence, u.name AS decided_by, d.created_at
  FROM commits c
  JOIN triples tr ON tr.subject_id = c.id AND tr.subject_type = 'commit'
    AND tr.predicate IN ('CONSTRAINED_BY', 'RESOLVES')
  JOIN decisions d ON tr.object_id = d.id AND tr.object_type = 'decision'
    AND d.status = 'active'
  LEFT JOIN triples tr2 ON tr2.subject_id = d.id AND tr2.predicate = 'MADE_BY'
  LEFT JOIN users u ON tr2.object_id = u.id
  WHERE c.file_paths && $1::text[]  -- $1 = ARRAY['src/auth/jwt.ts', 'src/auth/sessions.ts']
)
-- Step 2: Score semantic similarity between code_diff embedding and decision embeddings
SELECT rd.*, 
       1 - (rd.embedding <=> $2) AS conflict_score  -- $2 = embedding of the code diff
FROM related_decisions rd
WHERE 1 - (rd.embedding <=> $2) > 0.5  -- lower threshold than recall — catches more
ORDER BY conflict_score DESC;
```
> **Key insight:** This query finds violations **proactively** — it doesn't need a `VIOLATES` triple to already exist. The `VIOLATES` triple is created by the ingestion worker AFTER this query confirms a conflict.

### 3. Semantic Search (Hybrid: Vector + Graph)
```sql
-- Find decisions semantically similar to a query, then expand via graph
WITH semantic_matches AS (
  SELECT id, title, description, 
         1 - (embedding <=> $query_embedding) AS similarity
  FROM decisions
  WHERE 1 - (embedding <=> $query_embedding) > 0.7
  ORDER BY similarity DESC
  LIMIT 10
)
SELECT sm.*, t.url AS thread_url, u.name AS decided_by
FROM semantic_matches sm
LEFT JOIN triples t1 ON t1.subject_id = sm.id AND t1.predicate = 'DISCUSSED_IN'
LEFT JOIN threads t ON t1.object_id = t.id
LEFT JOIN triples t2 ON t2.subject_id = sm.id AND t2.predicate = 'MADE_BY'
LEFT JOIN users u ON t2.object_id = u.id;
```
