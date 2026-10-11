#!/usr/bin/env python3
"""
Per-paragraph simplification ladder.

The patient presses "explain more simply" repeatedly. Each press produces one
rung. Every rung is verified by the entity-check gate before the patient sees
it, and a rung that fails verification is discarded rather than shown.

Two design points worth stating:

1. ONE PARAGRAPH AT A TIME. Content omission by LLM simplifiers grows with
   input length (Picton et al. 2025), so the ladder never operates on a whole
   document. Short inputs also keep the gate's comparison tractable.

2. A FAILED RUNG DOES NOT BREAK THE LADDER. When rung N fails the gate, the
   patient stays on rung N-1 with a note, rather than being dropped back to the
   original. The last verified rung is always what is displayed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .gate import Verdict, check_simplification

Model = Callable[[str], str]

MAX_RUNG = 3

PROMPT = """Rewrite the medical text below so a patient can understand it.

Target reading level: {target}

Rules:
- Keep EVERY drug name, dose, number, date, and time exactly as written.
- Keep every instruction NOT to do something. Never drop a "do not".
- Do not add any information that is not in the text.
- Do not give advice or interpretation.
- Output only the rewritten text.

TEXT:
{text}

REWRITTEN:"""

TARGETS = {
    1: "around 8th grade. Replace clinical terms with everyday words.",
    2: "around 6th grade. Short sentences. Common words only.",
    3: "around 4th grade. Very short sentences. One idea per sentence.",
}


@dataclass
class Rung:
    level: int
    text: str
    verdict: Verdict | None = None
    readability: float | None = None

    @property
    def verified(self) -> bool:
        return self.verdict is None or self.verdict.passed


@dataclass
class Ladder:
    """
    The simplification state of one paragraph.

    Rung 0 is the clinician's original and is never generated, so it is always
    available as a fallback.
    """
    para_id: int
    rungs: list[Rung] = field(default_factory=list)
    blocked_at: int | None = None
    block_reasons: list[str] = field(default_factory=list)

    @property
    def current(self) -> Rung:
        return self.rungs[-1]

    @property
    def level(self) -> int:
        return self.current.level

    @property
    def can_simplify(self) -> bool:
        """False once the ladder is exhausted or a rung has been blocked."""
        return self.blocked_at is None and self.level < MAX_RUNG

    @property
    def status(self) -> str:
        if self.blocked_at is not None:
            return "blocked"
        return "exhausted" if self.level >= MAX_RUNG else "ok"


def readability(text: str) -> float | None:
    """Flesch-Kincaid grade. Optional: textstat may not be installed."""
    try:
        import textstat
        return round(textstat.flesch_kincaid_grade(text), 1)
    except Exception:
        return None


def start(para_id: int, original: str) -> Ladder:
    return Ladder(para_id, [Rung(0, original, None, readability(original))])


def simplify_once(
    ladder: Ladder, model: Model, use_ner: bool = True
) -> Ladder:
    """
    Add one rung, or record why it could not be added.

    The gate compares the new rung against the ORIGINAL (rung 0), not against
    the rung above it. Comparing to the previous rung would let a dose drift
    away gradually, one acceptable-looking step at a time.
    """
    if not ladder.can_simplify:
        return ladder

    target_level = ladder.level + 1
    candidate = model(PROMPT.format(
        target=TARGETS[target_level], text=ladder.current.text
    )).strip()

    original = ladder.rungs[0].text
    verdict = check_simplification(original, candidate, use_ner=use_ner)

    if not verdict.passed:
        ladder.blocked_at = target_level
        ladder.block_reasons = list(verdict.reasons)
        return ladder

    ladder.rungs.append(
        Rung(target_level, candidate, verdict, readability(candidate))
    )
    return ladder


def simplify_paragraph(
    para_id: int, original: str, model: Model, to_level: int = 1,
    use_ner: bool = True,
) -> Ladder:
    """Build a ladder up to the requested level, stopping early if blocked."""
    ladder = start(para_id, original)
    while ladder.level < min(to_level, MAX_RUNG) and ladder.can_simplify:
        simplify_once(ladder, model, use_ner=use_ner)
    return ladder
