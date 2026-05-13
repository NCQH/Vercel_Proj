import logging
import os
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_community.document_loaders import Docx2txtLoader, PyMuPDFLoader, TextLoader

logger = logging.getLogger(__name__)

SUPPORTED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".xls", ".txt", ".md"}
MAX_EXTRACTED_CHARS = int(os.getenv("MAX_EXTRACTED_CHARS", "600000"))
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "80"))
USE_MARKITDOWN_FOR_PDF = os.getenv("USE_MARKITDOWN_FOR_PDF", "false").lower() == "true"


def _read_text_file(path: str, filename: str, metadata: dict[str, Any]) -> list[Document]:
    loader = TextLoader(path, encoding="utf-8")
    docs = loader.load()
    total = 0
    for doc in docs:
        if total >= MAX_EXTRACTED_CHARS:
            doc.page_content = ""
        else:
            remaining = MAX_EXTRACTED_CHARS - total
            doc.page_content = (doc.page_content or "")[:remaining]
            total += len(doc.page_content or "")
        doc.metadata = {**(doc.metadata or {}), **metadata, "source": filename}
    return [doc for doc in docs if (doc.page_content or "").strip()]


def _read_pdf_lightweight(path: str, filename: str, metadata: dict[str, Any]) -> list[Document]:
    import fitz

    docs: list[Document] = []
    total_chars = 0
    with fitz.open(path) as pdf:
        page_count = min(len(pdf), MAX_PDF_PAGES)
        for page_index in range(page_count):
            if total_chars >= MAX_EXTRACTED_CHARS:
                break
            text = pdf.load_page(page_index).get_text("text") or ""
            remaining = MAX_EXTRACTED_CHARS - total_chars
            text = text[:remaining].strip()
            if not text:
                continue
            total_chars += len(text)
            docs.append(Document(
                page_content=text,
                metadata={**metadata, "source": filename, "page": page_index + 1, "loader": "pymupdf_light"},
            ))
    logger.info("Extracted %d PDF page(s), chars=%d from %s", len(docs), total_chars, filename)
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

    if ext == ".pdf":
        return _read_pdf_lightweight(path, filename, metadata)

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
