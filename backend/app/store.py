"""Document registry + FAISS vector store (cosine via normalised inner product), persisted on disk."""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from functools import lru_cache

from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_core.documents import Document

from . import config, ingest
from .models import get_embeddings

KINDS = {"notes", "textbook", "paper"}
# Embedders return unit vectors, so inner product == cosine similarity (FAISS ignores normalize_L2 here).
_FAISS_KW = dict(distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT)


class Store:
    def __init__(self) -> None:
        self.lock = threading.RLock()
        self.registry: dict[str, dict] = {}
        self.index: FAISS | None = None
        if config.REGISTRY_PATH.exists():
            self.registry = json.loads(config.REGISTRY_PATH.read_text())
        if (config.INDEX_DIR / "index.faiss").exists():
            self.index = FAISS.load_local(
                str(config.INDEX_DIR), get_embeddings(), allow_dangerous_deserialization=True, **_FAISS_KW
            )

    # ---- persistence -------------------------------------------------
    def _save(self) -> None:
        config.REGISTRY_PATH.write_text(json.dumps(self.registry, indent=2))
        if self.index is not None:
            self.index.save_local(str(config.INDEX_DIR))

    # ---- documents ---------------------------------------------------
    def list(self) -> list[dict]:
        return sorted(self.registry.values(), key=lambda m: m["created"], reverse=True)

    def pages(self, doc_id: str) -> list[tuple[int | None, str]]:
        p = config.TEXT_DIR / f"{doc_id}.json"
        return [tuple(x) for x in json.loads(p.read_text())] if p.exists() else []

    def add_document(self, filename: str, data: bytes, kind: str) -> dict:
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {sorted(KINDS)}")
        safe_name = Path(filename).name or "upload"
        pages = ingest.extract_pages(safe_name, data)
        if not any(t.strip() for _, t in pages):
            raise ValueError("No extractable text found (scanned PDFs need OCR first).")
        doc_id = uuid.uuid4().hex[:10]
        chunks = ingest.build_chunks(doc_id, filename, kind, pages)
        ids = [f"{doc_id}:{i}" for i in range(len(chunks))]
        with self.lock:
            if self.index is None:
                self.index = FAISS.from_documents(chunks, get_embeddings(), ids=ids, **_FAISS_KW)
            else:
                self.index.add_documents(chunks, ids=ids)
            (config.UPLOAD_DIR / f"{doc_id}_{safe_name}").write_bytes(data)
            (config.TEXT_DIR / f"{doc_id}.json").write_text(json.dumps(pages))
            meta = {
                "id": doc_id, "name": safe_name, "kind": kind, "pages": len(pages),
                "chunks": len(chunks), "created": time.time(),
            }
            self.registry[doc_id] = meta
            self._save()
        return meta

    def delete(self, doc_id: str) -> bool:
        with self.lock:
            meta = self.registry.pop(doc_id, None)
            if not meta:
                return False
            if self.index is not None:
                self.index.delete([f"{doc_id}:{i}" for i in range(meta["chunks"])])
            (config.TEXT_DIR / f"{doc_id}.json").unlink(missing_ok=True)
            for f in config.UPLOAD_DIR.glob(f"{doc_id}_*"):
                f.unlink(missing_ok=True)
            self._save()
            return True

    # ---- retrieval ---------------------------------------------------
    def search(self, query: str, doc_ids: list[str] | None = None, k: int = 6) -> list[tuple[Document, float]]:
        if self.index is None or not self.registry:
            return []
        allowed = set(doc_ids) if doc_ids else None
        flt = (lambda m: m.get("doc_id") in allowed) if allowed else None
        res = self.index.similarity_search_with_score(query, k=k, filter=flt, fetch_k=max(60, k * 12))
        return [(d, float(s)) for d, s in res]


@lru_cache
def get_store() -> Store:
    return Store()
