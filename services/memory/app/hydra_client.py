import os
import asyncio
from typing import List, Dict, Any, Optional
from hydra_db import AsyncHydraDB
from .models import NodeType, Predicate, NodeRef, Metadata

class HydraClient:
    def __init__(self):
        self.api_key = os.environ.get("HYDRADB_API_KEY")
        self.base_url = os.environ.get("HYDRADB_BASE_URL")
        if not self.api_key:
            raise ValueError("HYDRADB_API_KEY environment variable is not set")
        
        self.client = AsyncHydraDB(token=self.api_key)
