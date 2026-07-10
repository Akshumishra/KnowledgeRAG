from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.llm.rag.constant import RAGConstant

_tokenizer = None


def semantic_chunk_blocks(
    blocks: List[Dict[str, Any]],
    document_id: str,
    document_name: str,
    workspace_id: str,
    upload_date: Optional[str] = None,
    version: int = 1,
    chunk_size: int = RAGConstant.DEFAULT_CHUNK_SIZE,
) -> List[Dict[str, Any]]:
    if not upload_date:
        upload_date = datetime.now(timezone.utc).isoformat()

    chunks: List[Dict[str, Any]] = []
    chunk_index = 0

    pending_chunk: Optional[Dict[str, Any]] = None

    def _flush_pending():
        nonlocal chunk_index, pending_chunk
        if pending_chunk:
            if (
                _count_tokens(pending_chunk["content"]) < RAGConstant.MIN_CHUNK_SIZE
                and chunks
            ):
                chunks[-1]["content"] += "\n\n" + pending_chunk["content"]
                chunks[-1]["embedding_text"] = _build_embedding_text(
                    chunks[-1]["parent_heading"],
                    chunks[-1]["heading"],
                    chunks[-1]["content"],
                )
            else:
                pending_chunk["chunk_index"] = chunk_index
                pending_chunk["embedding_text"] = _build_embedding_text(
                    pending_chunk["parent_heading"],
                    pending_chunk["heading"],
                    pending_chunk["content"],
                )
                chunks.append(pending_chunk)
                chunk_index += 1
            pending_chunk = None

    for block in blocks:
        block_type = block.get("type", "text")
        content = block.get("content", "").strip()
        meta = block.get("metadata", {})

        if not content:
            continue

        if block_type in ("table", "figure", "image_description"):
            _flush_pending()

            chunk_id = str(uuid.uuid4())
            new_chunk = _make_chunk_base(
                chunk_id=chunk_id,
                content=content,
                chunk_type=block_type,
                document_id=document_id,
                document_name=document_name,
                workspace_id=workspace_id,
                page=meta.get("page", 1),
                heading=meta.get("heading", ""),
                parent_heading=meta.get("parent_heading", ""),
                upload_date=upload_date,
                version=version,
            )
            new_chunk["chunk_index"] = chunk_index
            new_chunk["embedding_text"] = _build_embedding_text(
                new_chunk["parent_heading"], new_chunk["heading"], new_chunk["content"]
            )
            chunks.append(new_chunk)
            chunk_index += 1
            continue

        sub_texts = _split_text_recursive(
            content, chunk_size, RAGConstant.DEFAULT_CHUNK_OVERLAP
        )

        for sub_text in sub_texts:
            sub_text = sub_text.strip()
            if not sub_text:
                continue

            sub_tokens = _count_tokens(sub_text)

            if pending_chunk:
                if pending_chunk["heading"] == meta.get("heading", ""):
                    pending_chunk["content"] += "\n\n" + sub_text
                    if (
                        _count_tokens(pending_chunk["content"])
                        >= RAGConstant.MIN_CHUNK_SIZE
                    ):
                        _flush_pending()
                    continue
                else:
                    _flush_pending()

            new_chunk_base = _make_chunk_base(
                chunk_id=str(uuid.uuid4()),
                content=sub_text,
                chunk_type="text",
                document_id=document_id,
                document_name=document_name,
                workspace_id=workspace_id,
                page=meta.get("page", 1),
                heading=meta.get("heading", ""),
                parent_heading=meta.get("parent_heading", ""),
                upload_date=upload_date,
                version=version,
            )

            if sub_tokens < RAGConstant.MIN_CHUNK_SIZE:
                pending_chunk = new_chunk_base
            else:
                new_chunk_base["chunk_index"] = chunk_index
                new_chunk_base["embedding_text"] = _build_embedding_text(
                    new_chunk_base["parent_heading"],
                    new_chunk_base["heading"],
                    new_chunk_base["content"],
                )
                chunks.append(new_chunk_base)
                chunk_index += 1

    _flush_pending()

    return chunks


def _build_embedding_text(parent_heading: str, heading: str, content: str) -> str:
    embedding_text = ""
    if parent_heading:
        embedding_text += parent_heading + "\n"
    if heading:
        embedding_text += heading + "\n"
    embedding_text += content
    return embedding_text


def _make_chunk_base(
    chunk_id: str,
    content: str,
    chunk_type: str,
    document_id: str,
    document_name: str,
    workspace_id: str,
    page: int,
    heading: str,
    parent_heading: str,
    upload_date: str,
    version: int,
) -> Dict[str, Any]:
    return {
        "chunk_id": chunk_id,
        "content": content,
        "type": chunk_type,
        "document_id": document_id,
        "document_name": document_name,
        "workspace_id": workspace_id,
        "page": page,
        "heading": heading,
        "parent_heading": parent_heading,
        "upload_date": upload_date,
        "version": version,
    }


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        import tiktoken

        _tokenizer = tiktoken.get_encoding("cl100k_base")
    return _tokenizer


def _count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(_get_tokenizer().encode(text))


def _split_text_recursive(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Langchain-style recursive character text splitter based on tokens."""
    separators = ["\n\n", "\n", ". ", " ", ""]
    return _do_split(text, separators, chunk_size, overlap)


def _do_split(
    text: str, separators: List[str], chunk_size: int, overlap: int
) -> List[str]:
    if _count_tokens(text) <= chunk_size:
        return [text]

    separator = separators[-1]
    new_separators = []
    for i, sep in enumerate(separators):
        if sep == "" or sep in text:
            separator = sep
            new_separators = separators[i + 1 :]
            break

    if separator:
        splits = text.split(separator)
    else:
        splits = list(text)

    good_splits = []
    current_doc = []
    current_length = 0

    for s in splits:
        if _count_tokens(s) > chunk_size:
            if current_doc:
                merged_text = separator.join(current_doc)
                if merged_text.strip():
                    good_splits.append(merged_text.strip())
                current_doc = []
                current_length = 0

            if new_separators:
                good_splits.extend(_do_split(s, new_separators, chunk_size, overlap))
            else:
                good_splits.extend(_hard_token_split(s, chunk_size, overlap))
        else:
            s_len = _count_tokens(s)
            sep_len = _count_tokens(separator) if current_doc else 0

            if current_length + s_len + sep_len > chunk_size and current_doc:
                merged_text = separator.join(current_doc)
                if merged_text.strip():
                    good_splits.append(merged_text.strip())
                while current_doc and current_length > overlap:
                    removed = current_doc.pop(0)
                    current_length -= _count_tokens(removed) + (
                        _count_tokens(separator) if current_doc else 0
                    )

                current_doc.append(s)
                current_length += s_len + (
                    _count_tokens(separator) if len(current_doc) > 1 else 0
                )
            else:
                current_doc.append(s)
                current_length += s_len + sep_len

    if current_doc:
        merged_text = separator.join(current_doc)
        if merged_text.strip():
            good_splits.append(merged_text.strip())

    return good_splits


def _hard_token_split(text: str, chunk_size: int, overlap: int) -> List[str]:
    tokens = _get_tokenizer().encode(text)
    chunks = []
    step = max(1, chunk_size - overlap)

    for i in range(0, len(tokens), step):
        chunk_tokens = tokens[i : i + chunk_size]
        chunks.append(_get_tokenizer().decode(chunk_tokens))
    return chunks
