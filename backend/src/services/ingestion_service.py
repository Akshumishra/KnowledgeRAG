from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.knowledge import Document
from src.llm.rag.loaders.universal_loader import load_document
from src.llm.rag.loaders.image_extractor import extract_and_describe_images
from src.llm.rag.chunking.section_builder import build_sections
from src.llm.rag.chunking.text_chunker import semantic_chunk_blocks
from src.llm.rag.embeddings.model import get_embedding_model
from src.models.knowledge import DocumentChunk

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".xls",
    ".csv",
    ".txt",
    ".md",
    ".markdown",
    ".json",
    ".xml",
}


class IngestionService:
    """
    Orchestrates the complete document ingestion pipeline.
    Runs in a background task after the upload API responds.
    """

    async def ingest(
        self,
        db: AsyncSession,
        document: Document,
        workspace_id: str,
        storage_provider,
        image_open_api_key: Optional[str] = None,
        image_processing_model: Optional[str] = "gpt-5-nano",
    ) -> None:

        file_path = document.storage_path
        logger.info(
            "Starting ingestion for document=%s path=%s", document.id, file_path
        )

        try:
            document.status = "processing"
            await db.flush()

            loop = asyncio.get_event_loop()
            blocks = await loop.run_in_executor(None, load_document, file_path)
            logger.info("Parsed %d blocks from %s", len(blocks), document.name)

            if image_open_api_key and file_path.endswith(".pdf"):
                image_blocks = await extract_and_describe_images(
                    file_path,
                    image_open_api_key,
                    image_processing_model,
                    document.name,
                    workspace_id,
                )
                blocks.extend(image_blocks)
                logger.info("Added %d image description blocks", len(image_blocks))

            upload_date = datetime.now(timezone.utc).isoformat()

            def _do_chunk():
                sections = build_sections(blocks)
                return semantic_chunk_blocks(
                    blocks=sections,
                    document_id=document.id,
                    document_name=document.name,
                    workspace_id=workspace_id,
                    upload_date=upload_date,
                    version=getattr(document, "version", 1),
                )

            chunks = await loop.run_in_executor(None, _do_chunk)
            logger.info("Generated %d chunks", len(chunks))

            if not chunks:
                raise ValueError("No content extracted from document")

            model = get_embedding_model()
            contents = [c.get("embedding_text", c["content"]) for c in chunks]

            batch_size = 64
            all_embeddings = []
            for i in range(0, len(contents), batch_size):
                batch = contents[i : i + batch_size]
                embs = await model.encode(batch, normalize_embeddings=True)
                all_embeddings.extend(embs)

            db_chunks = []
            for chunk, vector in zip(chunks, all_embeddings):
                metadata = {
                    "chunk_type": chunk.get("type"),
                    "chunk_id": chunk.get("chunk_id"),
                    "chunk_index": chunk.get("chunk_index"),
                    "document_name": chunk.get("document_name"),
                    "page": chunk.get("page", 1),
                    "heading": chunk.get("heading", ""),
                    "parent_heading": chunk.get("parent_heading", ""),
                    "upload_date": chunk.get("upload_date", ""),
                    "version": chunk.get("version", 1),
                    "image_url": chunk.get("metadata", {}).get("image_url", ""),
                }

                db_chunks.append(
                    DocumentChunk(
                        document_id=document.id,
                        workspace_id=workspace_id,
                        content=chunk["content"],
                        embedding=(
                            vector.tolist()
                            if hasattr(vector, "tolist")
                            else list(vector)
                        ),
                        metadata_json=metadata,
                    )
                )

            db.add_all(db_chunks)
            await db.flush()
            document.status = "ready"
            await db.flush()

            logger.info(
                "Ingestion complete: document=%s chunks=%d", document.id, len(chunks)
            )

        except Exception as e:
            logger.error("Ingestion failed for document=%s: %s", document.id, e)
            document.status = "failed"
            document.error_message = str(e)[:500]
            await db.flush()
