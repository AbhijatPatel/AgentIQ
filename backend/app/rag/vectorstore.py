
"""
Vector store for the RAG pipeline.

Wraps Chroma so the rest of the app never talks to Chroma directly -
just calls get_vectorstore() / add_documents() from here.

The vector store and embedding function are cached in memory so they
can be reused across multiple RAG retrieval requests.
"""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.rag.embeddings import get_embedding_function
from app.utils.logger import get_logger


logger = get_logger(__name__)


DEFAULT_PERSIST_DIR = "data/processed/chroma_db"
DEFAULT_COLLECTION_NAME = "agentiq_documents"


@lru_cache(maxsize=8)
def _get_cached_embedding_function():
    """
    Create the embedding function once and reuse it.

    The cache allows different vector-store configurations while
    avoiding repeated embedding model initialization.
    """
    logger.info("Initializing embedding function...")
    embedding_function = get_embedding_function()
    logger.info("Embedding function initialized.")
    return embedding_function


@lru_cache(maxsize=8)
def _get_cached_vectorstore(
    persist_directory: str,
    collection_name: str,
) -> Chroma:
    """
    Create and cache a Chroma vector store.

    Repeated calls with the same directory and collection reuse the
    same in-memory Chroma wrapper and embedding function.
    """
    Path(persist_directory).mkdir(
        parents=True,
        exist_ok=True,
    )

    logger.info(
        f"Initializing vector store: "
        f"collection={collection_name}, "
        f"directory={persist_directory}"
    )

    store = Chroma(
        collection_name=collection_name,
        embedding_function=_get_cached_embedding_function(),
        persist_directory=persist_directory,
    )

    logger.info(
        f"Vector store ready: collection={collection_name}"
    )

    return store


def get_vectorstore(
    persist_directory: str = DEFAULT_PERSIST_DIR,
    collection_name: str = DEFAULT_COLLECTION_NAME,
) -> Chroma:
    """
    Get (or create) the Chroma vector store.

    The vector store and embedding function are cached in memory,
    preventing repeated initialization during the lifetime of the
    application process.
    """
    return _get_cached_vectorstore(
        str(persist_directory),
        collection_name,
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
        logger.warning(
            "No chunks provided to add_documents; nothing stored."
        )
        return 0

    store = get_vectorstore(
        persist_directory,
        collection_name,
    )

    store.add_documents(chunks)

    logger.info(
        f"Added {len(chunks)} chunks to vector store"
    )

    return len(chunks)
