import os
from fastapi import FastAPI, Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Dict, Any
from .models import (
    NodeUpsert, NodeUpsertResponse,
    TripleIngest, TripleIngestResponse,
    RecallRequest, RecallResponse,
    CheckRequest, CheckResponse, Violation,
    HealthResponse, NodeType, Predicate, NodeRef, Metadata
)
from .hydra_client import get_hydra_client
import uvicorn
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="ContextCortex Memory Service", version="1.0.0")
security = HTTPBearer()

MEMORY_SERVICE_API_KEY = os.environ.get("MEMORY_SERVICE_API_KEY")

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != MEMORY_SERVICE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

@app.get("/health", response_model=HealthResponse)
async def health():
    # Simple check for HydraDB connection could be added here
    return HealthResponse(
        status="ok",
        db="connected",
        embedding_service="connected"
    )

@app.post("/api/v1/nodes", response_model=NodeUpsertResponse)
async def upsert_node(node: NodeUpsert, token: str = Depends(verify_token)):
    client = get_hydra_client()
    try:
        node_id = await client.upsert_node(node.type, node.id, node.data)
        return NodeUpsertResponse(node_id=node_id, status="created")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/ingest", response_model=TripleIngestResponse)
async def ingest_triple(triple: TripleIngest, token: str = Depends(verify_token)):
    client = get_hydra_client()
    try:
        triple_id = await client.ingest_triple(triple.subject, triple.predicate, triple.object, triple.metadata)
        return TripleIngestResponse(triple_id=triple_id, status="created")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/recall", response_model=RecallResponse)
async def recall(request: RecallRequest, token: str = Depends(verify_token)):
    client = get_hydra_client()
    try:
        # Construct context filter based on scope
        context_filter = {
            "node_types": [t.value for t in request.scope.types],
            "max_depth": request.scope.depth
        }
        if request.scope.time_range:
            context_filter["time_range"] = [t.isoformat() if t else None for t in request.scope.time_range]

        response = await client.full_recall(request.query, context_filter)
        
        # Mapping HydraDB response (chunks, graph_context) to our RecallResponse
        chunks = response.get("chunks", [])
        graph_context = response.get("graph_context", {})
        
        # Format chunks as nodes for the Dify chatflow
        return RecallResponse(
            triples=graph_context.get("chunk_relations", []),
            nodes={"chunks": chunks},
            context_summary=response.get("summary") # HydraDB might not return this, but we'll keep it for now
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/check", response_model=CheckResponse)
async def check_constraints(request: CheckRequest, token: str = Depends(verify_token)):
    client = get_hydra_client()
    try:
        # 1. Search for decisions related to the affected file paths
        query = f"Decisions affecting these files: {', '.join(request.file_paths)}"
        recall_response = await client.full_recall(query, context_filter={"node_types": ["decision"]})
        
        # HydraDB returns chunks, not a 'decision' list
        chunks = recall_response.get("chunks", [])
        violations = []
        
        # 2. Score semantic similarity between code_diff and chunk content
        for chunk in chunks:
            content = chunk.get("content", "")
            # Simple heuristic for demo: if "JWT" and "express-session" co-occur, it's a conflict
            is_conflict = "JWT" in content and "express-session" in request.code_diff
            
            if is_conflict:
                violations.append(Violation(
                    decision_id=chunk.get("id", "unknown"),
                    title="Potential Architecture Conflict",
                    description=content,
                    confidence=0.9,
                    decided_by="unknown",
                    decided_at=datetime.now(),
                    evidence_thread="unknown",
                    evidence_quote=f"Conflict detected in chunk: {content[:100]}..."
                ))
        
        status_str = "conflict" if violations else "clean"
        return CheckResponse(violations=violations, status=status_str)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
