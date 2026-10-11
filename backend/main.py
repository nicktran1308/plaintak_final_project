#!/usr/bin/env python3
"""
PlainTalk API.

Routes only. All logic lives in pipeline/. Session state is held in memory and
discarded when the process restarts: no accounts, no database, no patient data
at rest, per the SRS.

Run:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import config
from .pipeline.chat import ChatEngine
from .pipeline.intake import Document, load_document, load_text
from .pipeline.retrieve import Retriever, chunk_paragraphs
from .pipeline.simplify import Ladder, simplify_once, start
from .pipeline.translate import load_glossary, translate as run_translate

app = FastAPI(title="PlainTalk API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Session state, in memory only
# --------------------------------------------------------------------------
@dataclass
class Session:
    session_id: str
    language: str = config.DEFAULT_LANGUAGE
    documents: dict[str, Document] = field(default_factory=dict)
    ladders: dict[str, Ladder] = field(default_factory=dict)   # "doc:para" -> Ladder
    retriever: Retriever | None = None
    chat: ChatEngine | None = None


SESSIONS: dict[str, Session] = {}

_glossary = None
_embedder = None
_claude = None


def glossary():
    global _glossary
    if _glossary is None:
        _glossary = load_glossary(config.GLOSSARY_PATH)
    return _glossary


def embedder():
    global _embedder
    if _embedder is None:
        _embedder = config.make_embedder()
    return _embedder


def claude():
    global _claude
    if _claude is None:
        _claude = config.make_claude()
    return _claude


def get_session(session_id: str) -> Session:
    s = SESSIONS.get(session_id)
    if s is None:
        raise HTTPException(404, "session not found or expired")
    return s


# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------
class NewSession(BaseModel):
    language: str = config.DEFAULT_LANGUAGE


class AskBody(BaseModel):
    session_id: str
    question: str


class SimplifyBody(BaseModel):
    session_id: str
    doc_id: str
    para_id: int


class TranslateBody(BaseModel):
    session_id: str
    text: str


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {
        "ok": True,
        "model": config.MODEL_SIMPLIFY,
        "ner": config.USE_NER,
        "threshold": config.RETRIEVAL_THRESHOLD,
        "glossary_terms": len(glossary()),
        "api_key_present": bool(config.ANTHROPIC_API_KEY),
        "voyage_key_present": bool(config.VOYAGE_API_KEY),
    }


@app.post("/api/session")
def new_session(body: NewSession):
    sid = uuid.uuid4().hex[:12]
    s = Session(sid, body.language)
    s.retriever = Retriever(embedder(), threshold=config.RETRIEVAL_THRESHOLD)
    s.chat = ChatEngine(s.retriever, model=claude(), language=body.language)
    SESSIONS[sid] = s
    return {"session_id": sid, "language": body.language}


@app.post("/api/upload")
async def upload(session_id: str, file: UploadFile):
    s = get_session(session_id)
    suffix = Path(file.filename or "doc.pdf").suffix or ".pdf"
    with NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name
    try:
        doc = load_document(tmp_path, doc_id=Path(file.filename or "doc").stem)
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    s.documents[doc.doc_id] = doc
    s.retriever.add(chunk_paragraphs(doc.texts(), doc_id=doc.doc_id))
    return {
        "doc_id": doc.doc_id,
        "paragraphs": [
            {"para_id": p.para_id, "kind": p.kind, "text": p.text}
            for p in doc.paragraphs
        ],
    }


@app.post("/api/upload_text")
def upload_text(session_id: str, doc_id: str, text: str):
    """Paste-in path, and what the tests exercise."""
    s = get_session(session_id)
    doc = load_text(text, doc_id)
    s.documents[doc_id] = doc
    s.retriever.add(chunk_paragraphs(doc.texts(), doc_id=doc_id))
    return {
        "doc_id": doc_id,
        "paragraphs": [
            {"para_id": p.para_id, "kind": p.kind, "text": p.text}
            for p in doc.paragraphs
        ],
    }


@app.post("/api/simplify")
def simplify(body: SimplifyBody):
    """
    Add one rung to a paragraph's ladder.

    The response always reports the gate verdict, so the client renders what
    the gate decided rather than deciding for itself.
    """
    s = get_session(body.session_id)
    doc = s.documents.get(body.doc_id)
    if doc is None:
        raise HTTPException(404, "document not found")
    para = doc.get(body.para_id)
    if para is None:
        raise HTTPException(404, "paragraph not found")

    key = f"{body.doc_id}:{body.para_id}"
    ladder = s.ladders.get(key) or start(body.para_id, para.text)
    s.ladders[key] = ladder

    before = ladder.level
    simplify_once(ladder, claude(), use_ner=config.USE_NER)

    return {
        "para_id": body.para_id,
        "level": ladder.level,
        "text": ladder.current.text,
        "readability": ladder.current.readability,
        "original": ladder.rungs[0].text,
        "gate": "blocked" if ladder.blocked_at else "pass",
        "gate_reasons": ladder.block_reasons,
        "advanced": ladder.level > before,
        "can_simplify": ladder.can_simplify,
        "status": ladder.status,
    }


@app.post("/api/ask")
def ask(body: AskBody):
    """
    Answer a question, or refuse, or abstain.

    model_called is returned deliberately: it is the evidence that refusals
    and abstentions never reach the model.
    """
    s = get_session(body.session_id)
    r = s.chat.ask(body.question)
    return {
        "type": r.type.value,
        "text": r.text,
        "source": (
            {"chunk_id": r.source_chunk.chunk_id,
             "para_id": r.source_chunk.para_id,
             "text": r.source_chunk.text}
            if r.source_chunk else None
        ),
        "retrieval_score": round(r.retrieval_score, 3),
        "model_called": r.model_called,
        "added_to_handoff": r.added_to_handoff,
    }


@app.post("/api/translate")
def translate(body: TranslateBody):
    s = get_session(body.session_id)
    res = run_translate(
        body.text, claude(), glossary(),
        back_translate=True, use_ner=config.USE_NER,
    )
    return {
        "source": res.source_en,
        "translation": res.output_vi,
        "back_translation": res.back_en,
        "passed": res.passed,
        "reasons": res.reasons,
        "substitutions": res.substitutions,
        "action": res.action,
    }


@app.get("/api/handoff")
def handoff(session_id: str):
    s = get_session(session_id)
    return {"questions": s.chat.handoff_list()}


@app.delete("/api/session")
def end_session(session_id: str):
    SESSIONS.pop(session_id, None)
    return {"ended": True}
