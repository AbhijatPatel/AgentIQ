"""
Vector store for the RAG pipeline.

Wraps Chroma so the rest of the app never talks to Chroma directly -
just calls get_vectorstore() / add_documents() from here.
"""

from __future__ import annotations

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.rag.embeddings import get_embedding_function
from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_PERSIST_DIR = "data/processed/chroma_db"
DEFAULT_COLLECTION_NAME = "agentiq_documents"


def get_vectorstore(
    persist_directory: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Chroma:
    """
    Get (or create) the Chroma vector store, persisted to disk so
    documents don't need to be re-embedded every time the app restarts.
    """
    Path(persist_directory).mkdir(parents=True, exist_ok=True)

    return Chroma(
        collection_name=collection_name,
        embedding_function=get_embedding_function(),
        persist_directory=persist_directory,
    )


def add_documents(
    chunks: list[Document],
    persist_directory: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> int:
    """
    Embed and store document chunks in the vector store.
    Returns the number of chunks added.
    """
    if not chunks:
        logger.warning("No chunks provided to add_documents; nothing stored.")
        return 0

    store = get_vectorstore(persist_directory, collection_name)
    store.add_documents(chunks)
    logger.info(f"Added {len(chunks)} chunks to vector store")
    return len(chunks)