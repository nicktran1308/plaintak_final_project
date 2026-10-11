#!/usr/bin/env python3
"""
Retrieval and grounding for PlainTalk.

Chunks the patient's own documents, embeds them, and answers "which passage
supports this question?" — or reports that none does.

The threshold is the abstention trigger, not merely a ranking signal. When the
best passage scores below it, generation does not run at all. That exit happens
here, before chat.py ever reaches the model.

Embedding is injected rather than hard-coded, so the whole retrieval path can
be tested offline. Swap in a real embedder for production.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable, Protocol

Embedder = Callable[[list[str]], list[list[float]]]


# --------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------
@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    para_id: int
    text: str
    embedding: list[float] | None = None


def chunk_paragraphs(
    paragraphs: list[str], doc_id: str = "doc1", max_chars: int = 400
) -> list[Chunk]:
    """
    One chunk per paragraph, splitting only paragraphs that exceed max_chars.

    Paragraph boundaries are preserved because span-level citation needs to
    point at something the patient can actually see highlighted.
    """
    chunks: list[Chunk] = []
    for pi, para in enumerate(paragraphs):
        para = " ".join(para.split())
        if not para:
            continue
        if len(para) <= max_chars:
            chunks.append(Chunk(f"{doc_id}:p{pi}", doc_id, pi, para))
            continue
        # split on sentence boundaries, packing up to max_chars
        sents = re.split(r"(?<=[.!?])\s+", para)
        buf, part = "", 0
        for s in sents:
            if buf and len(buf) + len(s) + 1 > max_chars:
                chunks.append(Chunk(f"{doc_id}:p{pi}.{part}", doc_id, pi, buf.strip()))
                part += 1
                buf = s
            else:
                buf = f"{buf} {s}".strip()
        if buf:
            chunks.append(Chunk(f"{doc_id}:p{pi}.{part}", doc_id, pi, buf.strip()))
    return chunks


# --------------------------------------------------------------------------
# Retrieval
# --------------------------------------------------------------------------
def cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return 0.0 if na == 0 or nb == 0 else num / (na * nb)


@dataclass
class Hit:
    chunk: Chunk
    score: float


@dataclass
class RetrievalResult:
    hits: list[Hit] = field(default_factory=list)
    threshold: float = 0.0

    @property
    def best_score(self) -> float:
        return self.hits[0].score if self.hits else 0.0

    @property
    def grounded(self) -> bool:
        """True only if the best passage clears the threshold."""
        return self.best_score >= self.threshold

    @property
    def top(self) -> Chunk | None:
        return self.hits[0].chunk if self.hits else None


class Retriever:
    """
    In-memory vector store, scoped to one session.

    Session-scoped by design: the SRS forbids accounts and persistent storage,
    so there is nothing to persist and no patient data at rest.
    """

    def __init__(self, embedder: Embedder, threshold: float = 0.45):
        self.embedder = embedder
        self.threshold = threshold
        self.chunks: list[Chunk] = []
        self._qcache: dict[str, list[float]] = {}

    def add(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        vecs = self.embedder([c.text for c in chunks])
        for c, v in zip(chunks, vecs):
            c.embedding = v
        self.chunks.extend(chunks)

    def search(self, query: str, k: int = 3) -> RetrievalResult:
        if not self.chunks:
            return RetrievalResult([], self.threshold)
        qv = self._qcache.get(query)
        if qv is None:
            qv = self.embedder([query])[0]
            self._qcache[query] = qv
        scored = [Hit(c, cosine(qv, c.embedding or [])) for c in self.chunks]
        scored.sort(key=lambda h: h.score, reverse=True)
        return RetrievalResult(scored[:k], self.threshold)


# --------------------------------------------------------------------------
# Offline embedder for tests and development
# --------------------------------------------------------------------------
_STOP = set("a an the is are was were of to in on for with and or my your i you "
            "it this that do does did be been have has had at as by from".split())


class BagOfWordsEmbedder:
    """
    Deterministic lexical embedder for testing the retrieval PATH without an
    API key. It approximates relevance by shared vocabulary.

    NOT for production: it cannot match "tái khám" to "follow-up", which is
    exactly what real embeddings are for. Use it to verify that thresholding
    and abstention behave correctly, not to measure retrieval quality.
    """

    def __init__(self):
        self.vocab: dict[str, int] = {}

    def _tokens(self, text: str) -> list[str]:
        return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]

    def __call__(self, texts: list[str]) -> list[list[float]]:
        for t in texts:
            for tok in self._tokens(t):
                self.vocab.setdefault(tok, len(self.vocab))
        dim = max(len(self.vocab), 1)
        out = []
        for t in texts:
            v = [0.0] * dim
            for tok in self._tokens(t):
                v[self.vocab[tok]] += 1.0
            out.append(v)
        # pad earlier vectors if the vocabulary grew
        for c in getattr(self, "_registered", []):
            pass
        return out


def make_anthropic_embedder(api_key: str | None = None) -> Embedder:
    """
    Production embedder. Voyage AI is Anthropic's recommended embedding
    provider; swap in any provider that returns dense vectors.

    Left unimplemented deliberately: the retrieval path is testable without it,
    and wiring a provider is a configuration task rather than a design one.
    """
    raise NotImplementedError(
        "Wire an embedding provider here (e.g. voyageai, sentence-transformers). "
        "Use BagOfWordsEmbedder for offline tests."
    )
