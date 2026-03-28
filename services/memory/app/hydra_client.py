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

    async def upsert_node(self, node_type: NodeType, node_id: str, data: Dict[str, Any]) -> str:
        """
        Upsert a node. 
        - Decisions, Threads, Meetings go to knowledge.
        - Users might go to userMemory or knowledge.
        """
        # Mapping node types to HydraDB categories
        if node_type == NodeType.USER:
            # User memory example
            await self.client.userMemory.add(
                user_id=node_id,
                content=f"User {data.get('name')} with email {data.get('email')}",
                metadata=data
            )
            return node_id
        else:
            # Knowledge base for decisions, threads, etc.
            content = self._format_content(node_type, data)
            await self.client.upload.knowledge(
                content=content,
                metadata={
                    "node_type": node_type.value,
                    "node_id": node_id,
                    **data
                }
            )
            return node_id

    async def ingest_triple(self, subject: NodeRef, predicate: Predicate, object: NodeRef, metadata: Metadata) -> str:
        """
        Store a triple as a relationship in HydraDB.
        HydraDB often stores relationships as specialized knowledge or annotations.
        """
        relationship_text = f"({subject.type}:{subject.id}) -[{predicate.value}]-> ({object.type}:{object.id})"
        triple_id = f"{subject.id}_{predicate.value}_{object.id}"
        
        await self.client.upload.knowledge(
            content=relationship_text,
            metadata={
                "triple_id": triple_id,
                "subject_type": subject.type.value,
                "subject_id": subject.id,
                "predicate": predicate.value,
                "object_type": object.type.value,
                "object_id": object.id,
                "source": metadata.source,
                "confidence": metadata.confidence,
                "timestamp": metadata.timestamp.isoformat(),
                "raw_evidence": metadata.raw_evidence
            }
        )
        return triple_id

    async def full_recall(self, query: str, context_filter: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Call full_recall with the user's natural language query.
        """
        # In a real HydraDB SDK, parameters might vary.
        # Following the implementation plan's suggested signature.
        response = await self.client.recall.full_recall(
            query=query,
            context_filter=context_filter,
            alpha=0.8,  # Hybrid search balance (0.0 vector, 1.0 keyword/graph)
            recency_bias=0
        )
        return response

    def _format_content(self, node_type: NodeType, data: Dict[str, Any]) -> str:
        if node_type == NodeType.DECISION:
            return f"Decision: {data.get('title')}\nDescription: {data.get('description')}"
        elif node_type == NodeType.THREAD:
            return f"Thread Summary: {data.get('summary')}\nURL: {data.get('url')}"
        elif node_type == NodeType.COMMIT:
            return f"Commit: {data.get('message')}\nSHA: {data.get('sha')}\nFiles: {', '.join(data.get('file_paths', []))}"
        elif node_type == NodeType.MEETING:
            return f"Meeting: {data.get('title')}\nSummary: {data.get('summary')}"
        return str(data)

# Singleton instance
hydra_client = None

def get_hydra_client():
    global hydra_client
    if hydra_client is None:
        hydra_client = HydraClient()
    return hydra_client
