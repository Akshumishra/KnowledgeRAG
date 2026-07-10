from __future__ import annotations
import logging
import asyncio
from typing import List, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.knowledge import DocumentChunk
from src.llm.rag.embeddings.model import get_embedding_model

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self):
        self.embedder = get_embedding_model()

    def close(self):
        pass

    def _build_filters(self, workspace_id: str):
        # Tenant isolation is always required
        conditions = [DocumentChunk.workspace_id == workspace_id]
        return and_(*conditions)

    async def hybrid_search(
        self,
        session: AsyncSession,
        query: str,
        workspace_id: str,
        alpha: float = 0.8,
        limit: int = 10,
    ) -> List[dict]:
        """
        Executes semantic and keyword searches concurrently, normalizes their scores,
        and combines them using the given alpha weighting.
        alpha: Weight given to semantic search (0.0 to 1.0).
               0.8 means 80% semantic, 20% keyword.
        """
        # Execute both searches concurrently, fetching a bit more to ensure good overlap
        vector_task = self.vector_search(session, query, workspace_id, limit=limit * 2)
        keyword_task = self.keyword_search(
            session, query, workspace_id, limit=limit * 2
        )

        vector_results, keyword_results = await asyncio.gather(
            vector_task, keyword_task
        )

        # Helper to normalize scores [0, 1] based on the max score in the set
        def normalize_scores(results: List[dict]):
            if not results:
                return
            max_score = max((r["score"] for r in results), default=0.0)
            if max_score > 0:
                for r in results:
                    r["normalized_score"] = r["score"] / max_score
            else:
                for r in results:
                    r["normalized_score"] = 0.0

        normalize_scores(vector_results)
        normalize_scores(keyword_results)

        # Merge results keyed by chunk_id
        merged: dict[str, dict] = {}

        for res in vector_results:
            chunk_id = res.get("chunk_id") or res.get("id")
            res["final_score"] = res["normalized_score"] * alpha
            merged[chunk_id] = res

        for res in keyword_results:
            chunk_id = res.get("chunk_id") or res.get("id")
            if chunk_id in merged:
                merged[chunk_id]["final_score"] += res["normalized_score"] * (
                    1.0 - alpha
                )
            else:
                res["final_score"] = res["normalized_score"] * (1.0 - alpha)
                merged[chunk_id] = res

        # Convert dictionary back to list and sort by final_score
        final_results = list(merged.values())
        final_results.sort(key=lambda x: x["final_score"], reverse=True)

        # Ensure we just return the 'score' key as expected by downstream logic
        for r in final_results:
            r["score"] = r["final_score"]

        return final_results[:limit]

    async def vector_search(
        self,
        session: AsyncSession,
        query: str,
        workspace_id: str,
        limit: int = 10,
    ) -> List[dict]:
        """Pure vector (semantic) search with org and scope isolation."""
        embedded = await self.embedder.encode([query], normalize_embeddings=True)
        query_vector = embedded[0]
        filters = self._build_filters(workspace_id)
        distance = DocumentChunk.embedding.cosine_distance(query_vector).label(
            "distance"
        )
        stmt = (
            select(DocumentChunk, distance)
            .where(filters)
            .order_by(distance)
            .limit(limit)
        )
        try:
            result = await session.execute(stmt)
            rows = result.all()
        except Exception as e:
            logger.error("Vector search failed: %s", e)
            raise

        results = []
        for row in rows:
            chunk = row[0]
            dist = row[1]
            meta = chunk.metadata_json or {}

            results.append(
                {
                    "id": chunk.id,
                    "text": chunk.content,
                    "chunk_type": meta.get("chunk_type", "text"),
                    "document_id": chunk.document_id,
                    "document_name": meta.get("document_name", ""),
                    "collection_id": meta.get("collection_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "page": meta.get("page", 1),
                    "heading": meta.get("heading", ""),
                    "parent_heading": meta.get("parent_heading", ""),
                    "chunk_id": meta.get("chunk_id", chunk.id),
                    "score": 1.0 - float(dist) if dist is not None else 0.0,
                }
            )

        return results

    async def keyword_search(
        self,
        session: AsyncSession,
        query: str,
        workspace_id: str,
        limit: int = 10,
    ) -> List[dict]:
        """Pure Keyword search using PostgreSQL Full Text Search."""
        filters = self._build_filters(workspace_id)

        tsquery = func.plainto_tsquery("english", query)
        tsvector = func.to_tsvector("english", DocumentChunk.content)
        rank = func.ts_rank(tsvector, tsquery).label("rank")
        stmt = (
            select(DocumentChunk, rank)
            .where(and_(filters, tsvector.op("@@")(tsquery)))
            .order_by(rank.desc())
            .limit(limit)
        )

        try:
            result = await session.execute(stmt)
            rows = result.all()
        except Exception as e:
            logger.error("Keyword search failed: %s", e)
            return []

        results = []
        for row in rows:
            chunk = row[0]
            r = row[1]
            meta = chunk.metadata_json or {}

            results.append(
                {
                    "id": chunk.id,
                    "text": chunk.content,
                    "chunk_type": meta.get("chunk_type", "text"),
                    "document_id": chunk.document_id,
                    "document_name": meta.get("document_name", ""),
                    "collection_id": meta.get("collection_id", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                    "page": meta.get("page", 1),
                    "heading": meta.get("heading", ""),
                    "parent_heading": meta.get("parent_heading", ""),
                    "chunk_id": meta.get("chunk_id", chunk.id),
                    "score": float(r) if r is not None else 0.0,
                }
            )

        return results
