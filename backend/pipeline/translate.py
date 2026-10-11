#!/usr/bin/env python3
"""
Terminology-grounded English-to-Vietnamese translation for PlainTalk.

The central mechanism is that safety-critical content NEVER REACHES THE MODEL.
Doses, dates, drug names and verified glossary terms are replaced with opaque
placeholders before generation and restored afterwards. The model translates
only the prose around them.

    source    Hold metformin 500 mg PO BID until 11/14.
    protected ⟦0⟧ ⟦1⟧ ⟦2⟧ ⟦3⟧ until ⟦4⟧.
    model     ⟦0⟧ ⟦1⟧ ⟦2⟧ ⟦3⟧ cho đến ngày ⟦4⟧.
    restored  tạm ngưng metformin 500 mg uống hai lần mỗi ngày cho đến ngày 14/11.

A model that cannot see "500 mg" cannot drop it, round it, or alter it. This is
stronger than checking afterwards, though the gate still checks afterwards.

Sense selection uses the context rules in the reviewed glossary, so `hold`
resolves to `tạm ngưng` beside a medication and is left to the physical sense
elsewhere. Kong et al. (2026) documented the harm from getting this wrong.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .gate import Verdict, check_translation, extract_entities

Model = Callable[[str], str]

PLACEHOLDER = "⟦{}⟧"
RE_PLACEHOLDER = re.compile(r"⟦(\d+)⟧")


# --------------------------------------------------------------------------
# Glossary loading and sense selection
# --------------------------------------------------------------------------
@dataclass
class Sense:
    sense_id: str
    vi: str
    gloss: str = ""
    # default | requires | excludes | follows | preceded
    rule: str = "default"
    require_any: list[str] = field(default_factory=list)
    exclude_any: list[str] = field(default_factory=list)
    follows_any: list[str] = field(default_factory=list)
    preceded_any: list[str] = field(default_factory=list)
    do_not_use: list[str] = field(default_factory=list)
    confidence: str = ""
    tier: str = ""


@dataclass
class Term:
    en: str
    senses: list[Sense]
    safety_critical: bool = False


def load_glossary(path: str | Path) -> dict[str, Term]:
    """Load the reviewed glossary. Accepts a JSON array or JSONL."""
    text = Path(path).read_text(encoding="utf-8").strip()
    rows = (json.loads(text) if text.startswith("[")
            else [json.loads(l) for l in text.splitlines() if l.strip()])

    terms: dict[str, Term] = {}
    for row in rows:
        senses = []
        for s in row.get("senses", []):
            ctx = s.get("context", {}) or {}
            senses.append(Sense(
                sense_id=s.get("sense_id", ""),
                vi=(s.get("vi") or "").strip(),
                gloss=s.get("gloss", ""),
                rule=ctx.get("rule", "default"),
                require_any=[w.lower() for w in ctx.get("require_any", [])],
                exclude_any=[w.lower() for w in ctx.get("exclude_any", [])],
                follows_any=[w.lower() for w in ctx.get("follows_any", [])],
                preceded_any=[w.lower() for w in ctx.get("preceded_any", [])],
                do_not_use=s.get("do_not_use", []),
                confidence=s.get("confidence", ""),
                tier=s.get("tier", ""),
            ))
        # A term with no usable Vietnamese is not usable for substitution.
        senses = [s for s in senses if s.vi]
        if senses:
            terms[row["en"].lower()] = Term(
                en=row["en"], senses=senses,
                safety_critical=bool(row.get("safety_critical")),
            )
    return terms


def build_context(source: str, use_ner: bool = True) -> str:
    """
    Augment the source with synthetic context tokens derived from detected
    entities, so glossary context rules can fire on medication context without
    enumerating every drug name.

    "Hold metformin 500 mg" contains no word from a require_any list like
    ["medicine", "dose", "insulin"], but a drug entity and a dose entity are
    both present, which establishes the medication sense.
    """
    ents = extract_entities(source, use_ner=use_ner)
    tokens = []
    kinds = {e.kind for e in ents}
    if "drug" in kinds:
        tokens += ["medication", "medicine", "drug"]
    if "dose" in kinds:
        tokens += ["dose", "dosage"]
    if "freq" in kinds:
        tokens += ["frequency", "schedule"]
    if "route" in kinds:
        tokens += ["route", "medication"]
    # drug surfaces themselves, so require_any may name a specific drug
    tokens += [e.canon for e in ents if e.kind == "drug"]
    return source + (" \u2063" + " ".join(sorted(set(tokens))) if tokens else "")


# Special tokens usable in follows_any / preceded_any.
_SPECIAL = {
    "@date": re.compile(r"^\W*(\d{1,2}/\d{1,2}|january|february|march|april|may|"
                        r"june|july|august|september|october|november|december)", re.I),
    "@number": re.compile(r"^\W*\d"),
    "@clause": re.compile(r"^\W*(you|the|your|he|she|it|they|we|i)\b", re.I),
}


def _positional(patterns: list[str], text: str, before: bool) -> bool:
    """Match against the text immediately after (or before) the matched term."""
    if not text:
        return False
    probe = text[::-1] if before else text
    for pat in patterns:
        rx = _SPECIAL.get(pat)
        if rx is not None:
            # Reverse-scan for a preceding match by testing the tail directly.
            target = text[-24:] if before else text[:24]
            if before:
                if re.search(rx.pattern.lstrip("^"), target, re.I):
                    return True
            elif rx.match(text):
                return True
        elif pat in (probe[:40].lower() if before else text[:40].lower()):
            return True
    return False


def select_sense(term: Term, context: str,
                 after: str = "", before: str = "") -> Sense | None:
    """
    Choose the sense whose context rule fires. Specific rules are tried before
    the default, so `hold` next to `insulin` resolves to the medication sense.

    Returns None when no rule matches and there is no default: the caller must
    then leave the term to the model rather than guess a sense. For a
    safety-critical term this is reported, not silently ignored.
    """
    low = context.lower()
    # Positional rules first: they depend on the exact surroundings and are
    # therefore more specific than a whole-sentence keyword rule.
    order = {"follows": 0, "preceded": 0, "requires": 1, "excludes": 1}
    ranked = sorted(term.senses, key=lambda s: order.get(s.rule, 2))
    for s in ranked:
        if s.rule == "follows" and _positional(s.follows_any, after, before=False):
            return s
        if s.rule == "preceded" and _positional(s.preceded_any, before, before=True):
            return s
        if s.rule == "requires" and any(w in low for w in s.require_any):
            return s
        if s.rule == "excludes" and not any(w in low for w in s.exclude_any):
            return s
        if s.rule == "default":
            return s
    return None


# --------------------------------------------------------------------------
# Protection
# --------------------------------------------------------------------------
@dataclass
class Protected:
    text: str
    restore_vi: dict[str, str]       # placeholder -> Vietnamese / verbatim entity
    restore_en: dict[str, str]       # placeholder -> the ORIGINAL English surface
    substitutions: list[str] = field(default_factory=list)
    unresolved: list[str] = field(default_factory=list)


def protect(source: str, glossary: dict[str, Term], use_ner: bool = True) -> Protected:
    """
    Replace glossary terms and critical entities with placeholders.

    Glossary terms are replaced by their VIETNAMESE rendering, so the verified
    translation is substituted rather than generated. Entities are replaced by
    themselves, so they survive verbatim.
    """
    spans: list[tuple[int, int, str, str]] = []   # start, end, replacement, kind
    ctx = build_context(source, use_ner=use_ner)

    def overlaps(a: int, b: int) -> bool:
        return any(s0 < b and a < e0 for s0, e0, _, _ in spans)

    # Entities FIRST. A dose like "500 mg" must be claimed as one span before a
    # glossary entry for "mg" can split it in half.
    ents = sorted(extract_entities(source, use_ner=use_ner),
                  key=lambda e: -len(e.surface))
    for e in ents:
        if e.kind not in {"dose", "ratio", "date", "duration", "time", "drug"}:
            continue
        surface = e.surface
        # A duration such as "for 7 days" must not be frozen whole: doing so
        # leaves English sitting inside the Vietnamese output. Protect only the
        # number, so the surrounding unit word is translated around it.
        if e.kind == "duration":
            num = re.search(r"\d+(?:[.,]\d+)?", surface)
            if not num:
                continue
            surface = num.group(0)
        for m in re.finditer(re.escape(surface), source, re.I):
            if overlaps(m.start(), m.end()):
                continue
            spans.append((m.start(), m.end(), m.group(0), f"entity:{e.kind}"))
            break

    # Glossary terms fill in around them, longest match first.
    for en_key in sorted(glossary, key=len, reverse=True):
        term = glossary[en_key]
        for m in re.finditer(rf"(?<![\w]){re.escape(en_key)}(?![\w])", source, re.I):
            if overlaps(m.start(), m.end()):
                continue
            sense = select_sense(term, ctx,
                                 after=source[m.end():m.end() + 40],
                                 before=source[max(0, m.start() - 40):m.start()])
            if sense is None:
                if term.safety_critical:
                    spans.append((m.start(), m.end(), m.group(0), "unresolved"))
                continue
            spans.append((m.start(), m.end(), sense.vi, f"glossary:{sense.sense_id}"))

    spans.sort(key=lambda t: t[0])
    out, r_vi, r_en, subs, unresolved = [], {}, {}, [], []
    cursor = 0
    for i, (start, end, replacement, kind) in enumerate(spans):
        ph = PLACEHOLDER.format(i)
        out.append(source[cursor:start])
        out.append(ph)
        r_vi[ph] = replacement
        # The back-translation is compared against the English source, so
        # placeholders must restore to English there, not Vietnamese.
        r_en[ph] = source[start:end]
        cursor = end
        if kind == "unresolved":
            unresolved.append(source[start:end])
        else:
            subs.append(f"{source[start:end]} -> {replacement} [{kind}]")
    out.append(source[cursor:])
    return Protected("".join(out), r_vi, r_en, subs, unresolved)


def restore(text: str, mapping: dict[str, str]) -> tuple[str, list[str]]:
    """Put the protected content back. Reports any placeholder the model lost."""
    missing = [ph for ph in mapping if ph not in text]
    for ph, val in mapping.items():
        text = text.replace(ph, val)
    return text, missing


# --------------------------------------------------------------------------
# Translation
# --------------------------------------------------------------------------
PROMPT = """Translate the English text into Vietnamese for an older patient with limited health literacy.

Rules:
- Preserve every ⟦N⟧ placeholder EXACTLY as written. Do not translate, reorder the digits, add spaces inside, or remove them.
- Translate only the words around the placeholders.
- Use plain, respectful Vietnamese. Address the reader as "quý vị".
- Do not add information. Do not explain. Output only the translation.
{exemplars}
ENGLISH: {source}
VIETNAMESE:"""

BACK_PROMPT = """Translate this Vietnamese text into English literally.
Preserve every ⟦N⟧ placeholder exactly. Output only the translation.

VIETNAMESE: {text}
ENGLISH:"""


@dataclass
class TranslationResult:
    source_en: str
    output_vi: str | None
    back_en: str | None
    verdict: Verdict | None
    passed: bool
    reasons: list[str] = field(default_factory=list)
    substitutions: list[str] = field(default_factory=list)

    @property
    def action(self) -> str:
        return "show" if self.passed else "fallback_to_original"


def _format_exemplars(pairs: list[tuple[str, str]]) -> str:
    if not pairs:
        return "\n"
    lines = ["\nExamples of professionally translated patient material:"]
    for en, vi in pairs:
        lines.append(f"EN: {en}\nVI: {vi}")
    return "\n".join(lines) + "\n"


def translate(
    source_en: str,
    model: Model,
    glossary: dict[str, Term],
    exemplars: list[tuple[str, str]] | None = None,
    back_translate: bool = True,
    use_ner: bool = True,
) -> TranslationResult:
    """
    Full pipeline: protect, translate, restore, verify.

    Fails closed. Any lost placeholder, any gate failure, any unresolved
    safety-critical term returns passed=False and the caller shows the English
    original instead.
    """
    prot = protect(source_en, glossary, use_ner=use_ner)

    if prot.unresolved:
        return TranslationResult(
            source_en, None, None, None, False,
            [f"no sense matched for safety-critical term(s): {', '.join(prot.unresolved)}"],
            prot.substitutions,
        )

    raw_vi = model(PROMPT.format(
        exemplars=_format_exemplars(exemplars or []), source=prot.text
    )).strip()

    output_vi, missing = restore(raw_vi, prot.restore_vi)
    if missing:
        return TranslationResult(
            source_en, output_vi, None, None, False,
            [f"model dropped {len(missing)} protected placeholder(s): {', '.join(missing)}"],
            prot.substitutions,
        )

    back_en = None
    if back_translate:
        raw_back = model(BACK_PROMPT.format(text=raw_vi)).strip()
        back_en, _ = restore(raw_back, prot.restore_en)

    ctx = build_context(source_en, use_ner=use_ner)
    gate_gloss = {
        t.en: {"vi": s.vi, "do_not_use": s.do_not_use}
        for t in glossary.values()
        if (s := select_sense(t, ctx)) is not None
    }
    verdict = check_translation(
        source_en, output_vi, back_en, glossary=gate_gloss, use_ner=use_ner
    )
    return TranslationResult(
        source_en, output_vi, back_en, verdict, verdict.passed,
        list(verdict.reasons), prot.substitutions,
    )
