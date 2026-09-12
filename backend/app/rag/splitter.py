"""
Text splitter for the RAG pipeline.

Breaks loaded Documents into smaller overlapping chunks so they fit
well within embedding model limits and retrieval stays precise.
"""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.utils.logger import get_logger

logger = get_logger(__name__)

DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150


def split_documents(
    documents: list[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """
    Split documents into overlapping chunks.

    Overlap matters: without it, a sentence spanning a chunk boundary
    could lose context. A little overlap keeps nearby chunks coherent.

    Each chunk keeps the original document's metadata, plus a
    'chunk_index' marking its position within the source document.
    """
    if not documents:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[Document] = []
    for doc in documents:
        doc_chunks = splitter.split_documents([doc])
        for i, chunk in enumerate(doc_chunks):
            chunk.metadata["chunk_index"] = i
        chunks.extend(doc_chunks)

    logger.info(f"Split {len(documents)} documents into {len(chunks)} chunks")
    return chunks