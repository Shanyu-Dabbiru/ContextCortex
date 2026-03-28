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

