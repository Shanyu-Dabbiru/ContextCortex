-- NOTE: Embedding dimension is 768 by default. If your model uses a different
-- dimension, run: sed -i 's/vector(768)/vector(YOUR_DIM)/g' scripts/init_schema.sql
-- before executing this script.

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
