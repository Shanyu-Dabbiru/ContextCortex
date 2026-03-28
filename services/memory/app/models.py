from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Union
from datetime import datetime
from enum import Enum

class NodeType(str, Enum):
    USER = "user"
    DECISION = "decision"
    THREAD = "thread"
    COMMIT = "commit"
    MEETING = "meeting"

class Predicate(str, Enum):
    MADE_BY = "MADE_BY"
    DISCUSSED_IN = "DISCUSSED_IN"
    DECIDED_IN = "DECIDED_IN"
    RESOLVES = "RESOLVES"
    VIOLATES = "VIOLATES"
    SUPERSEDES = "SUPERSEDES"
    AUTHORED = "AUTHORED"
    AUTHORED_BY = "AUTHORED_BY"
    REVIEWED_BY = "REVIEWED_BY"
    REFERENCES = "REFERENCES"
    CONSTRAINED_BY = "CONSTRAINED_BY"

class NodeRef(BaseModel):
    type: NodeType
    id: str

class NodeUpsert(BaseModel):
    type: NodeType
    id: str
    data: Dict[str, Union[str, int, float, List[str], Dict[str, str], None]]

class Metadata(BaseModel):
    source: str
    timestamp: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    raw_evidence: Optional[str] = None

class TripleIngest(BaseModel):
    subject: NodeRef
    predicate: Predicate
    object: NodeRef
    metadata: Metadata

class RecallScope(BaseModel):
    types: List[NodeType] = [NodeType.DECISION, NodeType.THREAD, NodeType.USER]
    depth: int = Field(default=3, ge=1, le=5)
    time_range: Optional[List[Optional[datetime]]] = None

class RecallRequest(BaseModel):
    query: str
    scope: RecallScope = RecallScope()

class CheckRequest(BaseModel):
    code_diff: str
    file_paths: List[str]

class Violation(BaseModel):
    decision_id: str
    title: str
    description: str
    confidence: float
    decided_by: str
    decided_at: datetime
    evidence_thread: Optional[str] = None
    evidence_quote: Optional[str] = None

class CheckResponse(BaseModel):
    violations: List[Violation]
    status: str = "clean"  # "clean" or "conflict"

class NodeUpsertResponse(BaseModel):
    node_id: str
    status: str  # "created" or "updated"

class TripleIngestResponse(BaseModel):
    triple_id: str
    status: str  # "created" or "updated"

class RecallResponse(BaseModel):
    triples: List[Dict]
    nodes: Dict[str, List[Dict]]
    context_summary: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    db: str
    embedding_service: str
