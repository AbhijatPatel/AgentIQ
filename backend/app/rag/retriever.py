"""
Retriever for the RAG pipeline.

Given a natural-language query, returns the most relevant chunks along
with their source metadata and a relevance score - exactly what the
Researcher agent (Module 8) needs to ground its claims.
"""

from __future__ import annotations

from pathlib import Path

from app.rag.vectorstore import DEFAULT_COLLECTION_NAME, DEFAULT_PERSIST_DIR, get_vectorstore
from app.utils.logger import get_logger

logger = get_logger(__name__)


def retrieve(
    query: str,
    top_k: int = 4,
    persist_directory: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> list[dict]:
    """
    Retrieve the top_k most relevant chunks for a query.

    Returns a list of dicts, each containing:
        - content: the chunk text
        - source: original file path
        - filename: original file name
        - chunk_index: position within the source document
        - relevance_score: lower = more similar (Chroma returns distance)
    """
    if not query or not query.strip():
        logger.warning("Empty query passed to retrieve(); returning no results.")
        return []

    persist_path = Path(persist_directory)
    if not persist_path.exists() or not any(persist_path.iterdir()):
        logger.debug("Vector store directory is empty or does not exist; skipping RAG retrieval.")
        return []

    try:
        store = get_vectorstore(persist_directory, collection_name)
        results = store.similarity_search_with_score(query, k=top_k)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"Retrieval failed: {exc}")
        return []

    formatted = [
        {
            "content": doc.page_content,
            "source": doc.metadata.get("source"),
            "filename": doc.metadata.get("filename"),
            "chunk_index": doc.metadata.get("chunk_index"),
            "relevance_score": float(score),
        }
        for doc, score in results
    ]

    logger.info(f"Retrieved {len(formatted)} chunks for query: {query!r}")
    return formatted