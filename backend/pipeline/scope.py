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
# Informational override, checked BEFORE advice patterns.
#
# "How much water should I drink each day?" is a lookup, not a decision. A
# question opening with a quantity or time interrogative is asking what the
# document SAYS, even when it contains "should I". Over-refusal is its own
# failure: a system that declines every question is useless.
#
# Emergency patterns still win over this.
# --------------------------------------------------------------------------
INFORMATIONAL_LEAD = [
    r"^\s*how (much|many|long|often)\b",
    r"^\s*when (should|do|does|is|are|can)\b.*\b(go back|return|come back|appointment|follow.?up|take|start|expire)\b",
    r"^\s*(which|what) (medicine|medication|pill|drug|dose|time|day|date|number|test)s?\b",
    r"^\s*what (does|did) (the|my|this) (paper|document|form|sheet|instruction|report|result)",
    r"^\s*do i have to\b",
    r"^\s*(does|do) (the|this|my) (paper|document|form|sheet|instructions?)\b",
    # Vietnamese: a question ABOUT the document's contents is never advice,
    # even when it embeds "tôi có thể" or "tôi nên" inside the quoted content.
    r"^\s*(giấy|hướng dẫn|tài liệu|trong giấy|theo giấy)\b",
    r"\bgiấy (này|xuất viện|đó)\b.*\b(có|nói|dặn|ghi|nhắc|khuyên|cho biết)\b",
    r"\btrong giấy\b", r"\btheo giấy\b",
    # "at what time / how much should I take X" is a lookup, not a decision
    r"\btôi nên .* (vào lúc nào|khi nào|bao nhiêu|mấy giờ|ở đâu|thế nào)\b",
    r"^\s*bao nhiêu\b", r"^\s*mấy giờ\b",
    # "khi nào mới được uống lại?" = WHEN may I take it again -> a lookup.
    # Distinct from "tôi uống lại được hông?" = MAY I -> a permission request.
    r"^\s*(khi nào|chừng nào|bao giờ|ngày nào|mấy giờ|tới ngày nào)\b",
    r"^\s*(giấy|trong giấy|tờ giấy) (có )?(ghi|nói|để|dặn|kêu)\b",
    r"^\s*(thuốc|liều|giấy|ngày) .* (là )?(bao nhiêu|gì|nào)\b",
]

# --------------------------------------------------------------------------
# Advice-seeking: asks the system to make a clinical decision.
# --------------------------------------------------------------------------
ADVICE_EN = [
    # permission / decision
    r"\bshould i (stop|start|take|skip|double|restart|resume|continue|keep|change|switch|use|try)\b",
    r"\bwhat should i do\b", r"\bshould we\b",
    r"\bcan i (take|stop|start|skip|double|restart|resume|use)\b",
    r"\bis it (safe|ok|okay|alright|fine) to\b", r"\bam i (allowed|supposed) to\b",
    r"\bdo i need to (take|stop|start|worry|call|go)\b", r"\bwhat do i do\b",
    r"\bmust i\b", r"\bought i to\b",
    # medication decisions
    r"\b(stop|start|skip|double|restart|resume|change) (taking |my |the )?(medicine|medication|pills?|dose)",
    r"\bcan i drink\b", r"\bcan i eat\b",
    # diagnosis / prognosis
    r"\bwhat'?s wrong with me\b", r"\bam i (sick|dying|getting worse|ok)\b",
    # "do I have X" is a diagnosis request, but "what type of X do I have" and
    # "do I have to ..." are lookups. Require a condition-like object.
    # "Do I have kidney failure?" requests a diagnosis. "What type of diabetes
    # do I have?" and "Do I have to fast?" are lookups. Excluded by lookahead.
    r"^(?!.*\b(type|kind|sort) of\b).*\bdo i have\b(?!\s+to\b)",
    r"\bis (this|that|it) (bad|serious|dangerous|normal|nothing)\b",
    r"\bhow (long|much time) (do i have|have i got)\b",
    r"\bwill i (be ok|get better|die|recover)\b",
    r"\bis my .* (bad|dangerous|serious|too high|too low|normal)\b",
    r"\bwhat does (this|that|it) mean for me\b",
    r"\bwhat causes?\b.*\bmy\b",
    # --- added after evaluation-set authoring; the template-derived patterns
    # --- above missed every one of these naturalistic phrasings.
    r"\bwhat is safe to (take|eat|drink|do)\b",
    r"\bwhat can i (take|eat|drink|do)\b",
    r"\bis it (ok|okay|safe|alright|fine) (if|for me|to)\b",
    r"\bdoes (that|this|it) mean\b",
    r"\bdo you think\b",
    r"\bcan you (give|make|create|suggest|recommend|write) me\b",
    r"\bcan i (substitute|switch|swap|replace|change|split|halve|combine|mix)\b",
    r"\bdo i (really |actually )?need to\b",
    r"\bwhat (counts|qualifies) as\b",
    r"\bhow much .* (can|should) i (take|drink|eat)\b",
    r"\bwhat (dose|amount) should i\b",
    r"\b(is|are) (this|that|it|my|these) .* (safe|dangerous|serious|normal|too much|too little)\b",
    r"\bwill (this|that|it|i) (be ok|help|hurt|harm|make)\b",
    r"\bam i (going to|gonna)\b",
    r"\binstead of\b.*\?",
    r"\bcan i (lift|carry|climb|bend|kneel|swim|travel|fly)\b",
    r"\bshould i (weigh|measure|monitor|check|track|record)\b.*\b(myself|my)\b",
    r"\bwhat (exercises?|activities|foods?|drinks?|medicines?) (count|are|is)\b",
]
# NOTE: "hông" and "hổng" are the Southern spoken forms of "không". The first
# pattern set omitted them, and 29 of 30 authored Vietnamese advice questions
# leaked as a result. KHONG below matches all three forms.
KHONG = r"(không|hông|hổng|ko)"

ADVICE_VI = [
    # --- need / should ---
    rf"\btôi có cần\b.*{KHONG}", rf"\bcó nên\b.*{KHONG}",
    r"\btôi (có )?nên\b(?!.*\b(vào lúc nào|khi nào|bao nhiêu|mấy giờ)\b)", r"\bnên .* hay (không|hông|thôi)\b",
    # --- diagnosis / prognosis ---
    rf"\b(tôi|mình) có bị\b.*{KHONG}",
    r"\bcòn sống được\b", r"\bsống được (bao lâu|mấy năm)\b",
    rf"\bcó (nguy hiểm|nghiêm trọng|bình thường|nặng|sao)\b.*{KHONG}",
    r"\btôi (bị|mắc) (bệnh )?gì\b",
    rf"\bcó (cao|thấp|nhiều|nặng)\b.*(quá|lắm|dữ)\b.*{KHONG}",
    r"\b(cao|thấp|nhiều|nặng)\s+(quá|lắm|dữ)\b",
    # --- medication decisions ---
    rf"\btôi (có thể )?(uống|dùng|chích|ăn|lái|làm|đi|tập|xách|đổi|ngưng|nhịn|lấy)\b.*được\s+{KHONG}",
    r"\btôi (tự )?(đổi|thay|tăng|giảm|bớt|thêm|trộn|chích bù|uống bù)\b",
    r"\btôi (lén|tính|định)\b",
    r"\b(bỏ|quên) (một )?(liều|cữ|bữa)\b",
    r"\b(tăng|giảm) liều\b", r"\bchích (bù|thêm|gấp đôi)\b",
    r"\bthay (thuốc|cho thuốc)\b", r"\buống thay\b", r"\bthuốc nam\b",
    r"\btôi nên làm gì\b", r"\btôi phải làm gì\b", r"\btôi cần làm gì\b",
    r"\bcó an toàn\b",
    r"\btôi có khỏi\b",
    r"chỉ số .* có (cao|thấp|nhiều)",
    r"có (bị|làm) .* không",
]

# Explicit permission requests. These outrank the informational override,
# because "Giấy kêu bớt kali lại, vậy tôi ăn chuối già được hông?" opens like a
# document query but ends in a request for permission.
# "phải hông" / "đúng hông" are CONFIRMATION tags, not permission, and are
# excluded so that leading questions still reach the model to be corrected.
ADVICE_STRONG = [
    rf"(?<!phải )(?<!đúng )\bđược\s+{KHONG}\b",
    rf"\bcó sao\s+{KHONG}\b",
    rf"\bcó được\b.*{KHONG}",
    r"\btôi (có )?nên\b(?!.*\b(vào lúc nào|khi nào|bao nhiêu|mấy giờ)\b)",
    rf"\btôi có thể\b.*{KHONG}",
    # An elder proposing an action and appending a softener is asking
    # permission: "tôi uống 3 lít nước luôn nghen bác sĩ?"
    r"\b(tôi|mình|bác)\b[^?]{0,60}\b(nghen|nha|nhen)\s*(bác|con|bác sĩ|cô|chú)?\s*\?\s*$",
    rf"\b(tôi|mình) có bị\b.*{KHONG}",
    rf"\bkhông\s+lên\s+đâu\b",
    r"\b(tôi|mình)\b[^?]{0,70}\bcho\s+(nó\s+)?(mau|hết|xẹp|khoẻ)\b",
    r"\băn miếng\b.*\bkhông lên\b",
]

# --------------------------------------------------------------------------
# Document-content framing. Outranks even the strong permission tier, because
# "Giấy này có nhắc đến việc khi nào tôi có thể quay lại làm việc không?"
# ("does the paper mention when I can return to work?") asks what the document
# SAYS. The embedded "tôi có thể" is quoted subject matter, not a request.
# --------------------------------------------------------------------------
DOC_CONTENT = [
    r"^\s*(giấy|hướng dẫn|tài liệu|trong giấy|theo giấy|tờ giấy)\b",
    r"\bgiấy (này|xuất viện|đó)\b.*\b(có|nói|dặn|ghi|nhắc|khuyên|cho biết|yêu cầu|quy định)\b",
    r"\btrong giấy\b", r"\btheo giấy\b",
    r"^\s*(does|do|did) (the|this|my) (paper|document|form|sheet|instructions?|discharge)\b",
    r"\b(the|this|my) (paper|document|form|sheet|instructions?) (say|says|mention|mentions|list|lists|state|states)\b",
]

_RX = {
    "emergency": [re.compile(p, re.I) for p in EMERGENCY_EN + EMERGENCY_VI],
    "advice": [re.compile(p, re.I) for p in ADVICE_EN + ADVICE_VI],
    "info": [re.compile(p, re.I) for p in INFORMATIONAL_LEAD],
    "strong": [re.compile(p, re.I) for p in ADVICE_STRONG],
    "doc": [re.compile(p, re.I) for p in DOC_CONTENT],
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

    # Document framing wins ONLY when the whole question is about the
    # document. "Giấy kêu bớt kali lại, vậy tôi ăn chuối được không?" opens
    # with a document reference and then asks permission in a second clause,
    # so the tail is checked separately.
    if any(rx.search(q) for rx in _RX["doc"]):
        tail = q.split(",", 1)[1] if "," in q else ""
        if not (tail and any(rx.search(tail) for rx in _RX["strong"])):
            return ScopeResult(
                Scope.INFORMATIONAL, [],
                "asks what the document contains; an embedded request is quoted subject matter",
            )

    hits = [rx.pattern for rx in _RX["strong"] if rx.search(q)]
    if hits:
        return ScopeResult(
            Scope.ADVICE_SEEKING, hits,
            "explicit permission request; outranks the informational override",
        )

    if any(rx.search(q) for rx in _RX["info"]):
        return ScopeResult(
            Scope.INFORMATIONAL, [],
            "opens with a quantity or time interrogative; asking what the document says",
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
