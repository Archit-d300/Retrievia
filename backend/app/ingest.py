"""Parse uploads into page texts and section-aware chunks."""
from __future__ import annotations

import io
import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from . import config

HEADING_RE = re.compile(
    r"^\s*((chapter|unit|module|section|lecture)\s+[\dIVXivx]+[^\n]{0,80}|\d{1,2}(\.\d{1,2}){0,2}\.?\s+[A-Z][^\n]{3,70})\s*$",
    re.I,
)
ALLOWED = {".pdf", ".txt", ".md"}


def extract_pages(filename: str, data: bytes) -> list[tuple[int | None, str]]:
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return [(i + 1, (p.extract_text() or "").strip()) for i, p in enumerate(reader.pages)]
    if ext in (".txt", ".md"):
        return [(None, data.decode("utf-8", errors="ignore"))]
    raise ValueError(f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED))}")


def build_chunks(doc_id: str, name: str, kind: str, pages: list[tuple[int | None, str]]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=config.CHUNK_SIZE, chunk_overlap=config.CHUNK_OVERLAP)
    docs: list[Document] = []
    section = ""
    for page, text in pages:
        for line in text.splitlines():
            # Question papers have numbered questions, not chapters: don't mistake them for headings.
            if kind != "paper" and HEADING_RE.match(line):
                section = line.strip()[:90]
        for piece in splitter.split_text(text):
            docs.append(
                Document(
                    page_content=piece,
                    metadata={"doc_id": doc_id, "source": name, "kind": kind, "page": page, "section": section},
                )
            )
    return docs
