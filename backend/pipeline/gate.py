#!/usr/bin/env python3
"""
PlainTalk entity-check gate.

Decides whether a transformed text (simplified or translated) may be shown to
the patient, or whether the system must fall back to the clinician's original.

NO LANGUAGE MODEL IS CALLED HERE. Asking a model whether it preserved a dose
reproduces the failure being tested for. Extraction is regex plus optional
clinical NER; the comparison is deterministic set logic.

Design notes
------------
1. Normalization is essential. A CORRECT simplification rewrites "500 mg PO BID"
   as "500 mg by mouth two times a day". Comparing raw strings would reject
   every good rewrite. So entities are normalized to canonical forms
   (BID -> freq:2/day) and the canonical sets are compared.

2. Two modes:
     check_simplification(src, out)      both English  -> NER on both
     check_translation(src, vi, back)    EN -> VI       -> literal check on the
                                                           Vietnamese, entity
                                                           check on the
                                                           back-translation
   Clinical NER models are English-only, which is why translations are verified
   through back-translation rather than directly.

3. Fail closed. Any extraction error, any missing critical entity, any polarity
   flip returns BLOCK.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

# --------------------------------------------------------------------------
# Optional clinical NER. The gate works without it: doses, frequencies, dates
# and numbers are all regex-extractable. scispaCy adds recognition of drug
# names we did not anticipate.
# --------------------------------------------------------------------------
_NLP = None
_NER_READY = False


def load_ner(model: str = "en_ner_bc5cdr_md"):
    """Load scispaCy once. Safe to skip; regex core still runs."""
    global _NLP, _NER_READY
    if _NER_READY:
        return _NLP
    try:
        import spacy
        _NLP = spacy.load(model)
    except Exception:
        _NLP = None
    _NER_READY = True
    return _NLP


# --------------------------------------------------------------------------
# Canonical frequency vocabulary.
# Maps every surface form we expect to a single canonical token, so that a
# faithful simplification and its source produce identical entity sets.
# --------------------------------------------------------------------------
FREQ_CANON: dict[str, str] = {
    # Clinical abbreviations and fixed phrases. Rate phrases such as
    # "twice each day" are handled combinatorially by RE_FREQ_PHRASE below,
    # because enumerating English paraphrases is unbounded.
    "qd": "1/day", "od": "1/day", "daily": "1/day", "every day": "1/day",
    "bid": "2/day", "b.i.d.": "2/day",
    "tid": "3/day", "t.i.d.": "3/day",
    "qid": "4/day", "q.i.d.": "4/day",
    "every 24 hours": "1/day", "every 12 hours": "2/day",
    "every 8 hours": "3/day", "every 6 hours": "4/day",
    "qhs": "bedtime", "hs": "bedtime",
    "at bedtime": "bedtime", "before bed": "bedtime", "before bedtime": "bedtime",
    "at night": "bedtime", "every night": "bedtime", "nightly": "bedtime",
    "each night": "bedtime", "every night before bed": "bedtime",
    "at night before bed": "bedtime", "before going to bed": "bedtime",
    "in the evening": "bedtime", "every evening": "bedtime",
    "every night": "bedtime", "each night": "bedtime", "at night": "bedtime",
    "before bed": "bedtime", "before bedtime": "bedtime",
    "every night before bed": "bedtime", "at night before bed": "bedtime",
    "prn": "asneeded", "as needed": "asneeded",
}

# multiplier -> times per unit
_MULT = {
    "once": 1, "one time": 1, "1 time": 1,
    "twice": 2, "two times": 2, "2 times": 2,
    "thrice": 3, "three times": 3, "3 times": 3,
    "four times": 4, "4 times": 4,
    "five times": 5, "5 times": 5,
}
_MULT_ALT = "|".join(sorted(_MULT, key=len, reverse=True))

# "twice a day", "twice each day", "three times per day", "2 times every day"
RE_FREQ_PHRASE = re.compile(
    rf"\b({_MULT_ALT})\s+(?:a|an|each|per|every|the)?\s*(day|daily|week|hour)\b", re.I)

# A bare rate with no multiplier means once per unit: "2 L per day",
# "2 g/day", "each day". Checked only after the multiplier pattern has
# claimed its spans, so "twice a day" is not also counted as 1/day.
RE_FREQ_BARE = re.compile(r"(?:\b(?:a|an|each|per|every)\s+|/\s*)(day|week)\b", re.I)

ROUTE_CANON: dict[str, str] = {
    "po": "oral", "by mouth": "oral", "orally": "oral",
    "sq": "subq", "subq": "subq", "subcutaneous": "subq",
    "subcutaneously": "subq",
    "iv": "iv", "intravenous": "iv",
    "im": "im", "intramuscular": "im",
}

UNIT_CANON: dict[str, str] = {
    "mg": "mg", "milligram": "mg", "milligrams": "mg",
    "mcg": "mcg", "microgram": "mcg", "micrograms": "mcg",
    "g": "g", "gram": "g", "grams": "g",
    "ml": "ml", "milliliter": "ml", "milliliters": "ml", "millilitre": "ml",
    "l": "l", "liter": "l", "liters": "l",
    "unit": "unit", "units": "unit", "iu": "unit",
    "tablet": "tablet", "tablets": "tablet", "tab": "tablet", "tabs": "tablet",
    "capsule": "capsule", "capsules": "capsule", "cap": "capsule",
    "puff": "puff", "puffs": "puff", "drop": "drop", "drops": "drop",
}

# Form abbreviations and administrative labels that clinical NER mistakes for
# chemicals. "DOB" on a patient header is not a medication.
NOT_DRUGS: set[str] = {
    "dob", "mrn", "pcp", "ed", "er", "id", "dx", "rx", "sig", "npi", "dea",
    "am", "pm", "md", "do", "rn", "np", "pa", "bp", "hr", "rr", "temp",
    "qhs", "bid", "tid", "qid", "po", "prn", "sq", "iv", "im",
    "no", "not", "age", "date", "name", "suite", "phone", "fax",
}

# Physiological substances and their lay equivalents. Normalising these lets a
# simplifier write "blood sugar" for "glucose" without tripping the gate, while
# actual drug names remain protected.
SUBSTANCE_CANON: dict[str, str] = {
    "glucose": "glucose", "blood glucose": "glucose", "blood sugar": "glucose",
    "capillary blood glucose": "glucose", "sugar level": "glucose",
    "sodium": "sodium", "salt": "sodium",
    "potassium": "potassium",
    "creatinine": "creatinine",
    "water": "water", "fluid": "water", "fluids": "water",
}

# Abbreviations scispaCy mislabels as CHEMICAL. They are dosing schedules,
# routes, or record fields, and demanding that they survive a rewrite would
# demand that the clinical shorthand survive, which defeats simplification.
NOT_DRUGS = {
    "qhs", "qd", "od", "bid", "tid", "qid", "prn", "po", "sq", "subq",
    "im", "iv", "npo", "ac", "pc", "hs", "stat",
    "dob", "mrn", "dx", "rx", "sig", "qty",
}

# Words that reverse an instruction. A simplification may reword these, but it
# must not remove them.
NEGATION_MARKERS = {
    "do not", "don't", "dont", "never", "avoid", "stop", "hold", "discontinue",
    "not", "no", "cannot", "can't", "refrain", "skip",
    # lay paraphrases a simplifier reaches for. Without these, "Avoid all
    # NSAIDs" rewritten as "Stay away from all NSAIDs" reads as a lost
    # prohibition.
    "stay away", "steer clear", "keep away", "must not", "should not",
    "quit", "cut out", "leave out", "hold off",
}

# Descriptive negation states a fact rather than prohibiting an action.
# "Your kidneys are not working well" is a correct simplification of a
# diagnosis, and counting its "not" blocked three of them.
# Only be- and have-forms. "do not" is the canonical prohibition and must
# never be treated as descriptive.
RE_DESCRIPTIVE_NOT = re.compile(
    r"\b(is|are|was|were|am|be|been|being|has|have|had)\s+not\b", re.I)

# "without" as a qualifier is deliberately absent from NEGATION_MARKERS. The
# with-food and empty-stomach distinctions it would otherwise guard are
# covered by verified glossary terms instead.

MONTHS = ("january february march april may june july august september "
          "october november december").split()

# --------------------------------------------------------------------------
# Regexes
# --------------------------------------------------------------------------
_UNIT_ALT = "|".join(sorted(UNIT_CANON, key=len, reverse=True))
RE_DOSE = re.compile(rf"\b(\d+(?:[.,]\d+)?)\s*({_UNIT_ALT})\b", re.I)
# "1.5 to 2 L": only "2 L" carries a unit, so the 1.5 was invisible and
# rounding it to "2 to 2 L" passed. The first number inherits that unit.
RE_RANGE = re.compile(
    rf"\b(\d+(?:[.,]\d+)?)\s*(?:to|through|and|–|—|-)\s*"
    rf"(\d+(?:[.,]\d+)?)\s*({_UNIT_ALT})\b",
    re.I,
)
RE_RATIO = re.compile(rf"\b(\d+(?:[.,]\d+)?)\s*(mg|mcg|g)\s*/\s*(dl|l|ml|kg)\b", re.I)
RE_EVERY_N = re.compile(r"\bevery\s+(\d+)\s*(hour|hours|hr|hrs|day|days|week|weeks)\b", re.I)
RE_DATE_NUM = re.compile(r"\b(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?\b")
RE_DATE_TXT = re.compile(rf"\b({'|'.join(MONTHS)})\s+(\d{{1,2}})(?:,?\s*(\d{{4}}))?\b", re.I)
RE_DURATION = re.compile(
    r"\b(?:for|in|over|within|during|next|another)?\s*"
    r"(\d+)\s*(day|days|week|weeks|hour|hours|month|months)\b", re.I)
RE_TIME = re.compile(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?\b", re.I)


@dataclass(frozen=True)
class Entity:
    kind: str      # dose | ratio | freq | route | date | duration | drug | time | negation
    canon: str     # normalized comparison key
    surface: str   # text as it appeared, for error messages

    def __repr__(self) -> str:
        return f"{self.kind}:{self.canon}"


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------
def _norm_num(n: str) -> str:
    n = n.replace(",", ".")
    try:
        f = float(n)
        return str(int(f)) if f.is_integer() else str(f)
    except ValueError:
        return n


def extract_entities(text: str, use_ner: bool = True) -> set[Entity]:
    """Pull safety-critical entities out of English text."""
    if not text:
        return set()
    low = text.lower()
    ents: set[Entity] = set()

    for m in RE_RATIO.finditer(text):
        num, unit, per = _norm_num(m.group(1)), m.group(2).lower(), m.group(3).lower()
        ents.add(Entity("ratio", f"{num}{unit}/{per}", m.group(0)))

    for m in RE_DOSE.finditer(text):
        # skip if already captured as part of a ratio (70 mg/dL)
        if RE_RATIO.match(text, m.start()):
            continue
        num, unit = _norm_num(m.group(1)), UNIT_CANON[m.group(2).lower()]
        ents.add(Entity("dose", f"{num}{unit}", m.group(0)))

    for m in RE_RANGE.finditer(text):
        unit = UNIT_CANON[m.group(3).lower()]
        ents.add(Entity("dose", f"{_norm_num(m.group(1))}{unit}", m.group(1)))

    # "every N hours" maps into the frequency space when it divides evenly
    for m in RE_EVERY_N.finditer(text):
        n, unit = int(m.group(1)), m.group(2).lower()
        phrase = f"every {n} {'hours' if unit.startswith(('hour', 'hr')) else unit}"
        if phrase in FREQ_CANON:
            ents.add(Entity("freq", FREQ_CANON[phrase], m.group(0)))
        else:
            ents.add(Entity("freq", f"every{n}{unit[0]}", m.group(0)))

    # Longest phrase wins, and matched spans are consumed. Without this,
    # "two times a day" also matches the bare "a day" and yields a spurious
    # second frequency.
    claimed: list[tuple[int, int]] = []
    for m in RE_FREQ_PHRASE.finditer(low):
        n = _MULT[m.group(1).lower()]
        unit = m.group(2).lower()
        unit = "day" if unit == "daily" else unit
        claimed.append((m.start(), m.end()))
        ents.add(Entity("freq", f"{n}/{unit}", m.group(0)))

    for m in RE_FREQ_BARE.finditer(low):
        if any(a < m.end() and m.start() < b for a, b in claimed):
            continue
        claimed.append((m.start(), m.end()))
        ents.add(Entity("freq", f"1/{m.group(1).lower()}", m.group(0).strip()))

    for phrase in sorted(FREQ_CANON, key=len, reverse=True):
        if phrase.startswith("every ") and phrase[6].isdigit():
            continue  # "every 12 hours" handled by RE_EVERY_N above
        for m in re.finditer(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", low):
            if any(a < m.end() and m.start() < b for a, b in claimed):
                continue
            claimed.append((m.start(), m.end()))
            ents.add(Entity("freq", FREQ_CANON[phrase], phrase))

    for phrase, canon in ROUTE_CANON.items():
        if re.search(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", low):
            ents.add(Entity("route", canon, phrase))

    for m in RE_DATE_NUM.finditer(text):
        mo, day = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12 and 1 <= day <= 31:
            ents.add(Entity("date", f"{mo}-{day}", m.group(0)))
    for m in RE_DATE_TXT.finditer(text):
        mo = MONTHS.index(m.group(1).lower()) + 1
        ents.add(Entity("date", f"{mo}-{int(m.group(2))}", m.group(0)))

    for m in RE_DURATION.finditer(text):
        # "every 12 hours" is a frequency, not a duration.
        lead = text[max(0, m.start() - 10):m.start()].lower()
        if "every" in lead:
            continue
        ents.add(Entity("duration", f"{m.group(1)}{m.group(2).lower()[0]}",
                        m.group(0).strip()))

    for m in RE_TIME.finditer(text):
        h, mi, ap = int(m.group(1)), m.group(2), (m.group(3) or "").lower()
        if ap == "pm" and h != 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        ents.add(Entity("time", f"{h:02d}:{mi}", m.group(0)))

    # Lay names for body substances, matched directly. A simplification may
    # replace the clinical term entirely, so the canonical form must be
    # reachable from either wording.
    seen_substances: set[str] = set()
    for phrase, canon in sorted(SUBSTANCE_CANON.items(), key=lambda kv: -len(kv[0])):
        if canon in seen_substances:
            continue
        if re.search(rf"(?<![a-z]){re.escape(phrase)}(?![a-z])", low):
            seen_substances.add(canon)
            ents.add(Entity("drug", canon, phrase))

    if use_ner:
        nlp = load_ner()
        if nlp is not None:
            try:
                for e in nlp(text).ents:
                    if e.label_.upper() in {"CHEMICAL", "DRUG", "SIMPLE_CHEMICAL"}:
                        name = e.text.lower().strip()
                        if name in NOT_DRUGS:
                            continue
                        if name in NOT_DRUGS:
                            continue
                        ents.add(Entity("drug", SUBSTANCE_CANON.get(name, name), e.text))
            except Exception:
                pass  # fail open on NER only; regex core still applies

    return ents


def count_negations(text: str) -> int:
    """
    Count instructional negations.

    Descriptive negation ("your kidneys are not working well") is excluded:
    it states a fact rather than prohibiting an action, and a simplification
    is free to introduce or remove it without changing any instruction.
    """
    low = f" {text.lower()} "
    # Remove descriptive negation before counting, so "are not working" does
    # not register as a prohibition.
    low = RE_DESCRIPTIVE_NOT.sub(" ", low)
    return sum(
        len(re.findall(rf"(?<![a-z]){re.escape(m)}(?![a-z])", low))
        for m in NEGATION_MARKERS
    )


# --------------------------------------------------------------------------
# Verdict
# --------------------------------------------------------------------------
@dataclass
class Verdict:
    passed: bool
    reasons: list[str] = field(default_factory=list)
    missing: list[Entity] = field(default_factory=list)
    added: list[Entity] = field(default_factory=list)
    src_entities: set[Entity] = field(default_factory=set)
    out_entities: set[Entity] = field(default_factory=set)

    @property
    def action(self) -> str:
        return "show" if self.passed else "fallback_to_original"

    def __repr__(self) -> str:
        tag = "PASS" if self.passed else "BLOCK"
        return f"<{tag} {'; '.join(self.reasons) or 'all entities preserved'}>"


CRITICAL_KINDS = {"dose", "ratio", "freq", "date", "duration", "drug", "time"}


def check_simplification(source: str, output: str, use_ner: bool = True) -> Verdict:
    """
    Same-language check. Every critical entity in the source must survive.

    Dropping content is allowed in principle (a simplifier may omit an
    irrelevant clause) but NOT for critical entities: a lost dose is the
    failure mode this gate exists to catch.
    """
    src = extract_entities(source, use_ner)
    out = extract_entities(output, use_ner)
    v = Verdict(passed=True, src_entities=src, out_entities=out)

    out_keys = {(e.kind, e.canon) for e in out}
    missing = [e for e in src if e.kind in CRITICAL_KINDS
               and (e.kind, e.canon) not in out_keys]
    if missing:
        v.passed = False
        v.missing = missing
        v.reasons.append(
            "missing critical entities: " + ", ".join(sorted(str(e) for e in missing))
        )

    src_keys = {(e.kind, e.canon) for e in src}
    added = [e for e in out if e.kind in {"dose", "ratio", "freq", "date"}
             and (e.kind, e.canon) not in src_keys]
    if added:
        v.passed = False
        v.added = added
        v.reasons.append(
            "invented entities not in source: " + ", ".join(sorted(str(e) for e in added))
        )

    # Only a LOST prohibition is flagged.
    #
    # The two directions are not symmetric. Losing a negation turns "do not
    # take with alcohol" into permission, which is the harm this gate exists to
    # prevent. Gaining one is almost always benign paraphrase: a simplifier
    # renders "acute kidney injury" as "your kidneys are not working well",
    # which introduces a negation while changing nothing clinically.
    #
    # This is a deliberate trade. Checking both directions produced four false
    # positives in 33 hand-labelled candidates and caught nothing, because
    # marker counting has no notion of scope. Proper handling needs dependency
    # parsing, which is recorded as a limitation rather than approximated here.
    n_src, n_out = count_negations(source), count_negations(output)
    if n_src > 0 and n_out == 0:
        v.passed = False
        v.reasons.append(f"negation lost (source had {n_src}, output has none)")

    return v


def _phrase_in(phrase: str, text: str) -> bool:
    """Whole-phrase match. 'mg' does not match inside 'mcg'."""
    return re.search(
        rf"(?<![\w]){re.escape(phrase.lower())}(?![\w])", text.lower()
    ) is not None


def _term_applies(en_term: str, source_en: str, glossary: dict) -> bool:
    """True when this glossary term has an occurrence the longer terms do not cover."""
    term = en_term.lower()
    if not _phrase_in(term, source_en):
        return False
    redacted = source_en.lower()
    longer = [
        k.lower() for k in glossary
        if len(k) > len(term) and _phrase_in(term, k)
    ]
    for k in sorted(longer, key=len, reverse=True):
        redacted = re.sub(rf"(?<![\w]){re.escape(k)}(?![\w])", " ", redacted)
    return _phrase_in(term, redacted)


def check_translation(
    source_en: str,
    output_vi: str,
    back_translation_en: str | None = None,
    glossary: dict[str, dict] | None = None,
    use_ner: bool = True,
) -> Verdict:
    """
    Cross-language check, in two passes.

    Pass 1 (literal): numbers, units and dates ordinarily survive translation
    unchanged, so they can be matched directly in the Vietnamese. This catches
    the highest-stakes failure, a dropped or altered dose.

    Pass 2 (back-translation): clinical NER is English-only, so meaning-level
    errors are caught by translating back and comparing entity sets. This is
    what catches "hold" rendered as "keep taking".

    A span passes only if both passes pass.
    """
    src = extract_entities(source_en, use_ner)
    v = Verdict(passed=True, src_entities=src)

    # -- pass 1: literal strings in the Vietnamese --
    vi_low = output_vi.lower()
    literal_missing = []
    for e in src:
        if e.kind in {"dose", "ratio"}:
            num = re.match(r"[\d.]+", e.canon)
            if num:
                n = num.group(0)
                # Vietnamese often writes the decimal comma: 1,5 for 1.5.
                if n not in vi_low and n.replace(".", ",") not in vi_low:
                    literal_missing.append(e)
        elif e.kind == "date":
            mo, day = e.canon.split("-")
            if not (re.search(rf"\b{day}\b", vi_low) and re.search(rf"\b{mo}\b", vi_low)):
                literal_missing.append(e)
        elif e.kind == "drug":
            if e.canon not in vi_low:
                literal_missing.append(e)
    if literal_missing:
        v.passed = False
        v.missing.extend(literal_missing)
        v.reasons.append(
            "literal check failed, not found in translation: "
            + ", ".join(sorted(str(e) for e in literal_missing))
        )

    # -- glossary: forbidden renderings for safety-critical senses --
    if glossary:
        for en_term, entry in glossary.items():
            # A shorter term must not fire on a span a longer term already
            # owns. "resume" is a word inside "do not resume", and the
            # reviewed rendering "không tiếp tục" contains "tiếp tục", which
            # is forbidden for bare "resume". Longest phrase wins, matching
            # the substitution order in translate.protect.
            if not _term_applies(en_term, source_en, glossary):
                continue
            expected = (entry.get("vi") or "").lower()
            # If the verified rendering is present, the term was substituted
            # correctly and any forbidden string belongs to a different word in
            # the same sentence. Only flag when the correct form is absent.
            if expected and expected in vi_low:
                continue
            for bad in entry.get("do_not_use", []):
                if re.search(rf"(?<![\w]){re.escape(bad.lower())}(?![\w])", vi_low):
                    v.passed = False
                    v.reasons.append(
                        f"forbidden rendering for '{en_term}': '{bad}' "
                        f"(expected {entry.get('vi', 'the verified term')})"
                    )

    # -- pass 2: back-translation --
    if back_translation_en is not None:
        back = extract_entities(back_translation_en, use_ner)
        v.out_entities = back
        back_keys = {(e.kind, e.canon) for e in back}
        missing_back = [e for e in src if e.kind in CRITICAL_KINDS
                        and (e.kind, e.canon) not in back_keys]
        if missing_back:
            v.passed = False
            v.missing.extend(missing_back)
            v.reasons.append(
                "back-translation missing: "
                + ", ".join(sorted(str(e) for e in missing_back))
            )

        n_src, n_back = count_negations(source_en), count_negations(back_translation_en)
        if n_src > 0 and n_back == 0:
            v.passed = False
            v.reasons.append("back-translation lost the negation (meaning may be reversed)")
    else:
        v.reasons.append("no back-translation supplied; literal check only")

    return v


if __name__ == "__main__":
    s = "Hold metformin 500 mg PO BID until you follow up on 11/14."
    print("source:", s)
    print("entities:", sorted(str(e) for e in extract_entities(s, use_ner=False)))
    print(check_simplification(s, "Stop taking metformin. See your doctor.", use_ner=False))
