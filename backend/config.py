#!/usr/bin/env python3
"""
Configuration and model clients for PlainTalk.

Keys are read from the environment. Nothing here is ever sent to the browser.
"""

from __future__ import annotations

import os
from pathlib import Path

# Load .env from the project root without requiring python-dotenv.
_ENV = Path(__file__).resolve().parent.parent / ".env"
if _ENV.exists():
    for line in _ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Haiku is deliberate. If a small model plus verification beats a large model
# without it, that is a stronger result than using the biggest model available.
MODEL_SIMPLIFY = os.environ.get("PLAINTALK_MODEL", "claude-haiku-4-5-20251001")
MODEL_TRANSLATE = MODEL_SIMPLIFY
MODEL_CHAT = MODEL_SIMPLIFY

MAX_TOKENS = 1024
TEMPERATURE = 0.0          # determinism matters more than fluency here

# Placeholder until calibrated against the adversarial set (Week 11).
RETRIEVAL_THRESHOLD = float(os.environ.get("PLAINTALK_THRESHOLD", "0.30"))

DEFAULT_LANGUAGE = "vi"
GLOSSARY_PATH = Path(__file__).resolve().parent / "data" / "glossary_directive_DONE.jsonl"
EXEMPLAR_PATH = Path(__file__).resolve().parent / "data" / "exemplars.jsonl"

USE_NER = os.environ.get("PLAINTALK_USE_NER", "1") != "0"


# --------------------------------------------------------------------------
# Claude
# --------------------------------------------------------------------------
def make_claude(model: str = MODEL_SIMPLIFY):
    """
    Return a callable taking a prompt and returning text.

    Matches the signature the pipeline modules expect, so a stub can be swapped
    in for tests without changing any calling code.
    """
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Check your .env file.")

    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)

    def call(prompt: str) -> str:
        kwargs = {
            "model": model,
            "max_tokens": MAX_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        # Older/newer SDK versions differ on whether temperature is accepted
        # on this method. Determinism is preferable but not required.
        try:
            resp = client.messages.create(temperature=TEMPERATURE, **kwargs)
        except TypeError:
            resp = client.messages.create(**kwargs)
        return "".join(b.text for b in resp.content if b.type == "text")

    return call


# --------------------------------------------------------------------------
# Embeddings
# --------------------------------------------------------------------------
# Voyage is used over a local model deliberately. sentence-transformers pulls
# in torch, which requires NumPy 2, while spaCy 3.7.4 requires NumPy 1. The
# two cannot coexist in one environment. The entity-check gate depends on
# scispaCy, so spaCy wins and embeddings move to an API.
#
# LaBSE was only ever needed for the one-off corpus alignment, which is
# complete and whose scores are stored in pairs_scored.jsonl, so nothing is
# lost by removing it from the runtime.
VOYAGE_API_KEY = os.environ.get("VOYAGE_API_KEY", "")
EMBED_MODEL = os.environ.get("PLAINTALK_EMBED_MODEL", "voyage-3")


def make_embedder():
    """
    Return a callable taking a list of strings and returning a list of vectors.

    Must be cross-lingual: the patient asks in Vietnamese while the documents
    are English, so query and passage have to land in the same vector space.
    """
    if not VOYAGE_API_KEY:
        raise RuntimeError("VOYAGE_API_KEY is not set. Check your .env file.")

    import voyageai
    client = voyageai.Client(api_key=VOYAGE_API_KEY)

    def embed(texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), 128):          # provider batch limit
            batch = texts[i:i + 128]
            out.extend(client.embed(batch, model=EMBED_MODEL).embeddings)
        return out

    return embed
