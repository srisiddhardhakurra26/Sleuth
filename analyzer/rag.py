from __future__ import annotations

from typing import List

import numpy as np


def chunk_text(text: str, target_words: int = 300, overlap: int = 50) -> List[str]:
    words = text.split()
    if not words:
        return []
    chunks = []
    i = 0
    step = max(1, target_words - overlap)
    while i < len(words):
        chunks.append(" ".join(words[i : i + target_words]))
        i += step
    return chunks


def embed_texts(client, texts: List[str]) -> np.ndarray:
    BATCH = 100
    vecs = []
    for i in range(0, len(texts), BATCH):
        batch = texts[i : i + BATCH]
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=batch,
        )
        vecs.extend([e.values for e in result.embeddings])
    return np.array(vecs, dtype=np.float32)


def cosine_topk(qv: np.ndarray, matrix: np.ndarray, k: int = 5):
    q = qv / (np.linalg.norm(qv) + 1e-9)
    M = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    sims = M @ q
    idx = np.argsort(-sims)[:k]
    return idx, sims[idx]


class RAGIndex:
    """In-memory vector index over a fixed list of documents.

    Encapsulates the parallel chunk/source/vector arrays plus the search math —
    keeps session state to a single object instead of four loose keys.
    """

    def __init__(self, chunks: List[str], sources: List[str], vecs: np.ndarray):
        self.chunks = chunks
        self.sources = sources
        self.vecs = vecs

    @classmethod
    def build(cls, client, doc_text_fn, doc_names, chunk_words: int = 300) -> "RAGIndex":
        chunks: List[str] = []
        sources: List[str] = []
        for name in doc_names:
            text = doc_text_fn(name)
            for ch in chunk_text(text, target_words=chunk_words):
                chunks.append(ch)
                sources.append(name)
        if not chunks:
            raise RuntimeError("No text could be extracted.")
        vecs = embed_texts(client, chunks)
        return cls(chunks, sources, vecs)

    def search(self, client, query: str, k: int = 5):
        """Return list of (source_name, chunk_text, similarity)."""
        qv = embed_texts(client, [query])[0]
        idx, sims = cosine_topk(qv, self.vecs, k=k)
        return [
            (self.sources[i], self.chunks[i], float(sims[j]))
            for j, i in enumerate(idx)
        ]

    def __len__(self) -> int:
        return len(self.chunks)
