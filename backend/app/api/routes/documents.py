"""
Document upload endpoint.

Lets users add their own documents to the RAG vector store so the
Researcher agent can find them later. Enforces file-size and type
limits (Module 21 will harden this further).
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from app.rag.loader import DocumentLoadError, load_document
from app.rag.splitter import split_documents
from app.rag.vectorstore import add_documents
from app.schemas.response import DocumentUploadResponse
from app.utils.validators import sanitize_retrieved_content
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()

UPLOAD_DIR = Path("data/documents")
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile):
    """
    Upload a document, save it, and add it to the RAG vector store.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 10MB).")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    save_path = UPLOAD_DIR / file.filename

    save_path.write_bytes(contents)
    logger.info(f"Saved uploaded file: {save_path}")

    try:
        document = load_document(str(save_path))
        document.page_content = sanitize_retrieved_content(
            document.page_content, source_label=file.filename
        )
        chunks = split_documents([document])
        chunks_added = add_documents(chunks)
    except DocumentLoadError as exc:
        raise HTTPException(status_code=400, detail=f"Failed to process document: {exc}") from exc

    return DocumentUploadResponse(
        filename=file.filename,
        chunks_added=chunks_added,
        status="indexed",
    )