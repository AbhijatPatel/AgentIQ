"""
Document loader for the RAG pipeline.

Given a file path, reads its raw text content and wraps it into a
LangChain Document with metadata (source path, filename, file type).

Supports: .txt, .md, .pdf
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document

from app.utils.logger import get_logger

logger = get_logger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".csv", ".png", ".jpg", ".jpeg", ".webp"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class DocumentLoadError(Exception):
    """Raised when a document cannot be loaded."""


def _load_text_like(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _load_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentLoadError(
            "pypdf is required to load PDF files. Run: pip install pypdf"
        ) from exc

    reader = PdfReader(str(path))
    pages_text = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages_text)


def _load_image_reference(path: Path) -> str:
    """Creates a contextual placeholder representation for an uploaded reference image."""
    return f"[Attached Image Asset: {path.name} | File Size: {path.stat().st_size} bytes | Format: {path.suffix.upper().lstrip('.')}]"


def load_document(file_path: str) -> Document:
    """
    Load a single document from disk into a LangChain Document.

    Raises:
        DocumentLoadError: if the file doesn't exist, is empty, or is an
                            unsupported type.
    """
    path = Path(file_path)

    if not path.exists():
        raise DocumentLoadError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise DocumentLoadError(
            f"Unsupported file type '{path.suffix}'. Supported: {SUPPORTED_EXTENSIONS}"
        )

    logger.info(f"Loading document: {path.name}")

    if ext == ".pdf":
        content = _load_pdf(path)
    elif ext in IMAGE_EXTENSIONS:
        content = _load_image_reference(path)
    else:
        content = _load_text_like(path)

    if not content or not content.strip():
        raise DocumentLoadError(f"Document is empty: {file_path}")

    return Document(
        page_content=content,
        metadata={
            "source": str(path),
            "filename": path.name,
            "file_type": ext.lstrip("."),
        },
    )


def load_documents_from_directory(directory_path: str) -> list[Document]:
    """
    Load every supported document from a directory (non-recursive).

    Files that fail to load are skipped with a warning rather than
    failing the whole batch - one bad file shouldn't block everything else.
    """
    dir_path = Path(directory_path)
    if not dir_path.exists() or not dir_path.is_dir():
        raise DocumentLoadError(f"Directory not found: {directory_path}")

    documents: list[Document] = []
    for file_path in sorted(dir_path.iterdir()):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                documents.append(load_document(str(file_path)))
            except DocumentLoadError as exc:
                logger.warning(f"Skipping {file_path.name}: {exc}")

    logger.info(f"Loaded {len(documents)} documents from {directory_path}")
    return documents