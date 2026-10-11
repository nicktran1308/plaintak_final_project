#!/usr/bin/env python3
"""
Question-answering orchestration for PlainTalk.

Implements the project's central claim: when the system does not know, it does
not guess. Two exits fire BEFORE any model is contacted:

    question
      -> scope.classify()          advice-seeking?  -> REFUSE   (no model call)
      -> retriever.search()        below threshold? -> ABSTAIN  (no model call)
      -> model                     grounded answer with span citation

Both exits are branches in control flow, not instructions in a prompt. A
prompted refusal is advisory and can be argued past by rephrasing; a branch
cannot. Response.model_called records which path ran, so the property is
testable rather than merely claimed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from .retrieve import Chunk, Retriever
from .scope import Scope, classify

# A model is any callable taking a prompt and returning text. Injected so the
# orchestration can be tested without an API key.
Model = Callable[[str], str]


class ResponseType(Enum):
    ANSWER = "answer"
    REFUSAL = "refusal"
    ABSTAIN = "abstain"
    EMERGENCY = "emergency"


@dataclass
class Response:
    type: ResponseType
    text: str
    source_chunk: Chunk | None = None
    retrieval_score: float = 0.0
    model_called: bool = False
    added_to_handoff: bool = False
    debug: dict = field(default_factory=dict)

    @property
    def is_deferred(self) -> bool:
        """True when the system declined to answer for any reason."""
        return self.type in (
            ResponseType.REFUSAL, ResponseType.ABSTAIN, ResponseType.EMERGENCY
        )


# --------------------------------------------------------------------------
# Deterministic fallback messages.
# These are static strings, not generated text. They must be available even
# when the model is unreachable, and they must never vary.
# --------------------------------------------------------------------------
FALLBACKS = {
    ("refusal", "en"): (
        "That is a treatment decision, so I cannot answer it. I have added your "
        "question to the list for your doctor."
    ),
    ("refusal", "vi"): (
        "Đây là quyết định điều trị, nên tôi không thể trả lời. Tôi đã thêm câu "
        "hỏi này vào danh sách để quý vị hỏi bác sĩ."
    ),
    ("abstain", "en"): (
        "Your documents do not mention this. I have added your question to the "
        "list for your doctor."
    ),
    ("abstain", "vi"): (
        "Giấy tờ của quý vị không nói về điều này. Tôi đã thêm câu hỏi vào danh "
        "sách cho bác sĩ."
    ),
    ("emergency", "en"): (
        "This may be an emergency. Please call 911 or go to the nearest "
        "emergency room now."
    ),
    ("emergency", "vi"): (
        "Đây có thể là trường hợp khẩn cấp. Xin hãy gọi 911 hoặc đến phòng cấp "
        "cứu gần nhất ngay."
    ),
}

LANGUAGE_NAMES = {
    "en": "English",
    "vi": "Vietnamese",
}

ANSWER_PROMPT = """You are helping a patient understand their own medical document.

Answer ONLY using the passage below. Do not use any outside knowledge.
If the passage does not contain the answer, reply exactly: NOT_IN_DOCUMENT
Do not give medical advice, diagnosis, or treatment recommendations.
If the question contains a false assumption, correct it using the passage.

WRITE YOUR ANSWER IN {language}. The patient does not read English, so the
answer must be in {language} even though the passage is in English. Keep drug
names, doses, numbers and dates exactly as they appear in the passage.
The token NOT_IN_DOCUMENT is the one exception: write it in English.

PASSAGE:
{passage}

QUESTION: {question}

ANSWER:"""


class ChatEngine:
    def __init__(
        self,
        retriever: Retriever,
        model: Model | None = None,
        language: str = "en",
    ):
        self.retriever = retriever
        self.model = model
        self.language = language
        self.handoff: list[str] = []

    def _defer(self, kind: str, question: str, rtype: ResponseType, **kw) -> Response:
        self.handoff.append(question)
        return Response(
            type=rtype,
            text=FALLBACKS[(kind, self.language)],
            model_called=False,
            added_to_handoff=True,
            **kw,
        )

    def ask(self, question: str) -> Response:
        # ---- Exit 1: scope. No model call. ----
        sc = classify(question)
        if sc.scope is Scope.EMERGENCY:
            return self._defer("emergency", question, ResponseType.EMERGENCY,
                               debug={"matched": sc.matched})
        if sc.scope is Scope.ADVICE_SEEKING:
            return self._defer("refusal", question, ResponseType.REFUSAL,
                               debug={"matched": sc.matched, "reason": sc.reason})

        # ---- Exit 2: retrieval threshold. No model call. ----
        result = self.retriever.search(question)
        if not result.grounded:
            return self._defer("abstain", question, ResponseType.ABSTAIN,
                               retrieval_score=result.best_score,
                               debug={"threshold": result.threshold})

        # ---- Generation. Only reached when both checks pass. ----
        if self.model is None:
            raise RuntimeError("no model configured; cannot answer a grounded question")

        chunk = result.top
        raw = self.model(ANSWER_PROMPT.format(
            passage=chunk.text,
            question=question,
            language=LANGUAGE_NAMES.get(self.language, "English"),
        ))

        # The model may still decline. Honour it rather than overriding.
        if "NOT_IN_DOCUMENT" in raw:
            r = self._defer("abstain", question, ResponseType.ABSTAIN,
                            retrieval_score=result.best_score,
                            debug={"reason": "model reported passage insufficient"})
            r.model_called = True
            return r

        return Response(
            type=ResponseType.ANSWER,
            text=raw.strip(),
            source_chunk=chunk,
            retrieval_score=result.best_score,
            model_called=True,
        )

    def handoff_list(self) -> list[str]:
        """Questions the system declined, for the printable clinician sheet."""
        return list(self.handoff)
