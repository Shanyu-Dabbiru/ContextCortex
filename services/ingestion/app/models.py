from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class IngestMessageRequest(BaseModel):
    user: str
    text: str
    thread_id: str
    timestamp: Optional[str] = None

class SimulatePRRequest(BaseModel):
    author: str
    code_diff: str
    file_paths: List[str]
    repo: Optional[str] = "unknown"
    pr_number: Optional[int] = 0

class TripleNode(BaseModel):
    type: str
    id: str

class Triple(BaseModel):
    subject: TripleNode
    predicate: str
    object: TripleNode
    evidence: str
    confidence: float

class ExtractionResponse(BaseModel):
    triples: List[Triple]
