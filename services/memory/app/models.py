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
