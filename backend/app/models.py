"""Hugging Face model wrappers: embeddings (local or API) and a token-counting chat LLM."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from huggingface_hub import InferenceClient
from langchain_core.embeddings import Embeddings

from . import config


class HFEmbeddings(Embeddings):
    """LFM2.5-Embedding is asymmetric: queries and documents need different prefixes."""

    def __init__(self) -> None:
        self._local = None
        self._client = None

    def _encode(self, texts: list[str], prefix: str) -> list[list[float]]:
        if not texts:
            return []
        texts = [prefix + t for t in texts]
        if config.EMBED_MODE == "local":
            if self._local is None:
                try:
                    from sentence_transformers import SentenceTransformer

                    self._local = SentenceTransformer(config.EMBED_MODEL, trust_remote_code=False)
                except Exception:
                    fallback_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
                    from sentence_transformers import SentenceTransformer

                    self._local = SentenceTransformer(fallback_model, trust_remote_code=False)
            vecs = self._local.encode(texts, batch_size=16, normalize_embeddings=True)
            return np.asarray(vecs, dtype="float32").tolist()
        if self._client is None:
            self._client = InferenceClient(model=config.EMBED_MODEL, token=config.HF_TOKEN)
        out: list[np.ndarray] = []
        for i in range(0, len(texts), 16):
            arr = np.asarray(self._client.feature_extraction(texts[i : i + 16]), dtype="float32")
            if arr.ndim == 3:  # token-level output -> mean pool
                arr = arr.mean(axis=1)
            out.extend(arr)
        mat = np.vstack(out)
        mat /= np.linalg.norm(mat, axis=1, keepdims=True) + 1e-9
        return mat.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._encode(texts, config.DOC_PREFIX)

    def embed_query(self, text: str) -> list[float]:
        return self._encode([text], config.QUERY_PREFIX)[0]


class LLM:
    """Thin chat wrapper that reports token usage so the UI can show the cost of each answer."""

    def __init__(self, model: str) -> None:
        self.model = model
        self.client = InferenceClient(model=model, token=config.HF_TOKEN, provider=config.HF_PROVIDER)

    def chat(self, system: str, user: str, max_tokens: int = 400, temperature: float = 0.1) -> tuple[str, int]:
        r = self.client.chat_completion(
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = (r.choices[0].message.content or "").strip()
        return text, int(getattr(r.usage, "total_tokens", 0) or 0)


@lru_cache
def get_embeddings() -> Embeddings:
    return HFEmbeddings()


@lru_cache
def get_llm() -> LLM:
    return LLM(config.LLM_MODEL)


@lru_cache
def get_grader() -> LLM:
    return get_llm() if config.GRADER_MODEL == config.LLM_MODEL else LLM(config.GRADER_MODEL)
