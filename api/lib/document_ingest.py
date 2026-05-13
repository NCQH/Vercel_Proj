import logging
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader, TextLoader

logger = logging.getLogger(__name__)

SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".txt", ".md"}


def _read_text_file(path: str, filename: str, metadata: dict[str, Any]) -> list[Document]:
    loader = TextLoader(path, encoding="utf-8")
    docs = loader.load()
    for doc in docs:
        doc.metadata = {**(doc.metadata or {}), **metadata, "source": filename}
    return docs


def _fallback_load(path: str, filename: str, ext: str, metadata: dict[str, Any]) -> list[Document]:
    if ext == ".pdf":
        docs = PyMuPDFLoader(path).load()
    elif ext == ".docx":
        docs = Docx2txtLoader(path).load()
    elif ext in {".txt", ".md"}:
        docs = TextLoader(path, encoding="utf-8").load()
    else:
        docs = []

    for doc in docs:
        doc.metadata = {**(doc.metadata or {}), **metadata, "source": filename}
    return docs


def extract_documents_from_file(path: str, filename: str, metadata: dict[str, Any] | None = None) -> list[Document]:
    """Extract upload content into LangChain Documents.

    Uses MarkItDown first for rich document formats and falls back to legacy loaders
    for supported PDF/DOCX/TXT/MD files. Spreadsheet and PowerPoint formats rely on
    MarkItDown and return no documents if conversion fails.
    """
    metadata = metadata or {}
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_DOCUMENT_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {ext or 'unknown'}")

    if ext in {".txt", ".md"}:
        return _read_text_file(path, filename, metadata)

    try:
        from markitdown import MarkItDown

        converter = MarkItDown()
        result = converter.convert(path)
        text_content = str(getattr(result, "text_content", "") or "").strip()
        if text_content:
            return [Document(page_content=text_content, metadata={**metadata, "source": filename, "loader": "markitdown"})]
        logger.warning("MarkItDown returned empty text for %s", filename)
    except Exception:
        logger.warning("MarkItDown conversion failed for %s; trying fallback loader", filename, exc_info=True)

    return _fallback_load(path, filename, ext, metadata)
