"""
Embeddings for the RAG pipeline.

Uses a local sentence-transformers model, so no API key or external
service is required. The model downloads once (~80MB) and then runs
fully offline on your machine.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings

from app.utils.logger import get_logger

logger = get_logger(__name__)

# all-MiniLM-L6-v2: small, fast, good enough quality for this project.
# Produces 384-dimensional vectors.
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def get_embedding_function(model_name: str = DEFAULT_EMBEDDING_MODEL) -> HuggingFaceEmbeddings:
    """
    Return a cached embedding function.

    lru_cache ensures the (fairly large) model loads into memory only
    once per process, not once per call.
    """
    logger.info(f"Loading embedding model: {model_name} (first call may take a while)")
    return HuggingFaceEmbeddings(model_name=model_name)