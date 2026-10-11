#!/usr/bin/env python3
"""
Scope classifier for PlainTalk.

Decides whether a patient question is answerable from their document, or
whether it asks for a medical decision the system must refuse.

NO LANGUAGE MODEL IS CALLED. This is deliberate and is the whole point: a
prompt asking a model to decline advice-seeking questions is advisory, and the
same models are documented to answer questions they should decline. Here the
refusal is a branch in control flow, so it cannot be argued past by rephrasing.

BILINGUAL BY DESIGN. The patient asks in Vietnamese. Translating the question
to English before classifying would require a model call BEFORE the refusal,
which would defeat the purpose. So patterns are matched in both languages.

>>> VIETNAMESE PATTERNS NEED NATIVE REVIEW <<<
The Vietnamese patterns below are a starting set. They must be reviewed and
extended by a native speaker before evaluation. Under-matching here is a
safety failure: a missed advice-seeking question reaches the model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Scope(Enum):
    INFORMATIONAL = "informational"   # answerable from the document
    ADVICE_SEEKING = "advice_seeking"  # refuse: diagnosis, prognosis, treatment
    EMERGENCY = "emergency"            # refuse and direct to emergency care


@dataclass
class ScopeResult:
    scope: Scope
    matched: list[str]
    reason: str

    @property
    def must_refuse(self) -> bool:
        return self.scope in (Scope.ADVICE_SEEKING, Scope.EMERGENCY)


# --------------------------------------------------------------------------
# Emergency. Checked first: these override everything, including a question
# that would otherwise look informational.
# --------------------------------------------------------------------------
EMERGENCY_EN = [
    r"\bchest pain\b", r"\bcan'?t breathe\b", r"\btrouble breathing\b",
    r"\bstruggling to breathe\b", r"\bunconscious\b", r"\bpassed out\b",
    r"\bbleeding (a lot|heavily|badly)\b", r"\boverdose[d]?\b",
    r"\btook too (much|many)\b", r"\bsuicid",
]
EMERGENCY_VI = [
    r"đau ngực",           # chest pain
    r"khó thở",            # difficulty breathing
    r"không thở được",     # cannot breathe
    r"bất tỉnh",           # unconscious
    r"ngất",               # fainted
    r"chảy máu nhiều",     # bleeding heavily
    r"uống quá liều",      # overdose
    r"uống quá nhiều thuốc",
]

# --------------------------------------------------------------------------
# Advice-seeking: asks the system to make a clinical decision.
# --------------------------------------------------------------------------
ADVICE_EN = [
    # permission / decision
    r"\bshould i\b", r"\bshould we\b", r"\bcan i (take|stop|start|skip|double|restart|resume)\b",
    r"\bis it (safe|ok|okay|alright|fine) to\b", r"\bam i (allowed|supposed) to\b",
    r"\bdo i need to\b", r"\bwhat should i do\b", r"\bwhat do i do\b",
    r"\bmust i\b", r"\bought i to\b",
    # medication decisions
    r"\b(stop|start|skip|double|restart|resume|change) (taking |my |the )?(medicine|medication|pills?|dose)",
    r"\bcan i drink\b", r"\bcan i eat\b",
    # diagnosis / prognosis
    r"\bwhat'?s wrong with me\b", r"\bdo i have\b", r"\bam i (sick|dying|getting worse|ok)\b",
    r"\bis (this|that|it) (bad|serious|dangerous|normal|nothing)\b",
    r"\bhow (long|much time) (do i have|have i got)\b",
    r"\bwill i (be ok|get better|die|recover)\b",
    r"\bis my .* (bad|dangerous|serious|too high|too low|normal)\b",
    r"\bwhat does (this|that|it) mean for me\b",
    r"\bwhat causes?\b.*\bmy\b",
]
ADVICE_VI = [
    # permission / decision — note: "có" is frequently dropped in speech
    r"tôi có nên", r"có nên .* không",
    r"tôi có thể .* không",
    r"(có )?được không",              # "uống được không", "ăn được không"
    r"(uống|ăn|dùng|làm) .* được không",
    r"có sao không",                  # "is anything wrong / is it ok"
    r"(có )?an toàn không",
    r"tôi nên làm gì", r"tôi phải làm gì", r"tôi cần làm gì",
    r"nên .* hay (không|nên)",        # "should I ... or not"

    # medication decisions
    r"(uống|dùng) lại",
    r"ngưng (uống|dùng|thuốc)", r"ngừng (uống|dùng|thuốc)",
    r"bỏ (một )?liều", r"quên (uống|liều)",
    r"tăng liều", r"giảm liều",
    r"(uống|dùng) thêm", r"(uống|dùng) chung với",
    r"đổi thuốc",

    # diagnosis / prognosis
    r"tôi (bị|mắc) (bệnh )?gì",
    r"(có )?nguy hiểm không",
    r"(có )?nghiêm trọng không",
    r"(có )?bình thường không",
    r"(có )?nặng không",
    r"tôi có khỏi không", r"có hết không",
    r"tôi sống được bao lâu",
    # "too high/low" — quá, lắm, and bare comparatives all occur
    r"(cao|thấp|nhiều|nặng) (quá|lắm)( không)?",
    r"có (cao|thấp|nhiều|nặng)",
    r"như (vậy|thế) có",              # "is it like that ...?"
]

_RX = {
    "emergency": [re.compile(p, re.I) for p in EMERGENCY_EN + EMERGENCY_VI],
    "advice": [re.compile(p, re.I) for p in ADVICE_EN + ADVICE_VI],
}


def classify(question: str) -> ScopeResult:
    """Classify a patient question. Deterministic; no model call."""
    q = " ".join((question or "").split())
    if not q:
        return ScopeResult(Scope.INFORMATIONAL, [], "empty question")

    hits = [rx.pattern for rx in _RX["emergency"] if rx.search(q)]
    if hits:
        return ScopeResult(
            Scope.EMERGENCY, hits,
            "matched an emergency pattern; direct the patient to urgent care",
        )

    hits = [rx.pattern for rx in _RX["advice"] if rx.search(q)]
    if hits:
        return ScopeResult(
            Scope.ADVICE_SEEKING, hits,
            "asks for a clinical decision (diagnosis, prognosis, or treatment)",
        )

    return ScopeResult(Scope.INFORMATIONAL, [], "answerable from the document if present")


if __name__ == "__main__":
    for q in [
        "When is my follow-up appointment?",
        "Can I restart the metformin?",
        "Tôi có thể uống lại metformin không?",
        "Khi nào tôi tái khám?",
        "I'm having chest pain, what do I do?",
    ]:
        r = classify(q)
        print(f"{r.scope.value:16} {q}")
