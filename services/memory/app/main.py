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
