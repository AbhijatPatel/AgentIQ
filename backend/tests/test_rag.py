"""
Tests for the RAG pipeline.

Loader and splitter tests run instantly (no ML model needed).
Vectorstore/retriever tests are integration tests that use the REAL
local embedding model - the first run will be slower (model loads
into memory), but no internet/API calls happen after the model is
downloaded once by pip/sentence-transformers.
"""

import pytest

from app.rag.loader import DocumentLoadError, load_document, load_documents_from_directory
from app.rag.splitter import split_documents
from app.rag.vectorstore import add_documents, get_vectorstore
from app.rag.retriever import retrieve


# ---------------------------------------------------------------------------
# Loader tests
# ---------------------------------------------------------------------------

def test_load_document_reads_txt_file(tmp_path):
    file_path = tmp_path / "sample.txt"
    file_path.write_text("Hello world, this is a test document.")

    doc = load_document(str(file_path))

    assert "Hello world" in doc.page_content
    assert doc.metadata["filename"] == "sample.txt"
    assert doc.metadata["file_type"] == "txt"


def test_load_document_raises_on_missing_file():
    with pytest.raises(DocumentLoadError):
        load_document("does_not_exist.txt")


def test_load_document_raises_on_unsupported_extension(tmp_path):
    file_path = tmp_path / "sample.exe"
    file_path.write_text("binary-ish content")

    with pytest.raises(DocumentLoadError):
        load_document(str(file_path))


def test_load_document_raises_on_empty_file(tmp_path):
    file_path = tmp_path / "empty.txt"
    file_path.write_text("")

    with pytest.raises(DocumentLoadError):
        load_document(str(file_path))


def test_load_documents_from_directory_skips_bad_files(tmp_path):
    (tmp_path / "good.txt").write_text("Real content here.")
    (tmp_path / "empty.txt").write_text("")
    (tmp_path / "ignored.exe").write_text("nope")

    docs = load_documents_from_directory(str(tmp_path))

    assert len(docs) == 1
    assert docs[0].metadata["filename"] == "good.txt"


# ---------------------------------------------------------------------------
# Splitter tests
# ---------------------------------------------------------------------------

def test_split_documents_produces_chunks_with_index(tmp_path):
    file_path = tmp_path / "long.txt"
    file_path.write_text("word " * 500)  # long enough to force multiple chunks

    doc = load_document(str(file_path))
    chunks = split_documents([doc], chunk_size=200, chunk_overlap=20)

    assert len(chunks) > 1
    assert chunks[0].metadata["chunk_index"] == 0
    assert chunks[1].metadata["chunk_index"] == 1
    assert chunks[0].metadata["filename"] == "long.txt"


def test_split_documents_handles_empty_list():
    assert split_documents([]) == []


# ---------------------------------------------------------------------------
# Vectorstore + Retriever integration tests (uses real local embeddings)
# ---------------------------------------------------------------------------

def test_add_and_retrieve_documents(tmp_path):
    persist_dir = str(tmp_path / "chroma_test")

    file_path = tmp_path / "facts.txt"
    file_path.write_text(
        "The Eiffel Tower is located in Paris, France. "
        "It was completed in 1889 and is made of iron."
    )

    doc = load_document(str(file_path))
    chunks = split_documents([doc])

    added_count = add_documents(chunks, persist_directory=persist_dir)
    assert added_count == len(chunks)

    results = retrieve("Where is the Eiffel Tower?", top_k=2, persist_directory=persist_dir)

    assert len(results) > 0
    assert "Eiffel Tower" in results[0]["content"]
    assert results[0]["filename"] == "facts.txt"


def test_retrieve_with_empty_query_returns_empty_list(tmp_path):
    persist_dir = str(tmp_path / "chroma_test_empty")
    results = retrieve("", persist_directory=persist_dir)
    assert results == []