#!/usr/bin/env python3
"""
Apply the two grammatical fixes identified by the LLM pre-screen.

Both are substitution-order faults rather than terminology errors: the
Vietnamese chosen is correct in the context it was authored against, and wrong
in a context the author did not test. Neither was caught by the live smoke
test, because that test only exercised clause contexts.

A1  until   "cho đến khi" needs a clause after it. Before a date it produces
            "cho đến khi ngày 14/11", which is ungrammatical. A second sense
            keyed on a following date supplies "cho đến".

A2  refill  English uses "refills" as a counted noun ("0 refills"), while the
            authored Vietnamese is a verb phrase, producing "0 lấy thêm thuốc".
            A second sense keyed on a preceding number supplies the noun form.
"""
import json
import shutil
from pathlib import Path

P = Path("backend/data/glossary_directive_DONE.jsonl")
shutil.copy(P, P.with_suffix(".jsonl.bak2"))
rows = json.loads(P.read_text(encoding="utf-8"))

UNTIL_DATE = {
    "sense_id": "until.date",
    "gloss": "up to a stated date or number, with no clause following",
    "vi": "cho đến",
    "vi_alternatives": ["đến"],
    "context": {"rule": "follows", "follows_any": ["@date", "@number"]},
    "do_not_use": ["cho đến khi", "trừ khi"],
    "do_not_use_reason": (
        "'cho đến khi' requires a clause after it, so before a date it yields "
        "the ungrammatical 'cho đến khi ngày 14/11'. 'trừ khi' means 'unless'."),
    "register": "plain",
    "regional_note": "Same in Northern and Southern usage.",
    "confidence": "high",
    "reviewer_note": (
        "Added after an LLM pre-screen flagged that the clause form breaks "
        "before a date. Author-confirmed rendering: 'cho đến ngày 14/11'."),
}

REFILL_COUNT = {
    "sense_id": "refill.count",
    "gloss": "a counted remaining fill of a prescription, as a noun",
    "vi": "lần lấy thuốc",
    "vi_alternatives": ["lần lãnh thuốc"],
    "context": {"rule": "preceded", "preceded_any": ["@number"]},
    "do_not_use": ["lấy thêm thuốc"],
    "do_not_use_reason": (
        "The verb phrase produces '0 lấy thêm thuốc' when a number precedes it. "
        "The counted noun gives '0 lần lấy thuốc'."),
    "register": "plain",
    "regional_note": "'lãnh thuốc' is common in Southern usage.",
    "confidence": "high",
    "reviewer_note": (
        "Added after an LLM pre-screen flagged the part-of-speech mismatch. "
        "Author-confirmed rendering: 'Còn 0 lần lấy thuốc'."),
}

changed = []
for r in rows:
    if r["en"] == "until":
        if not any(s["sense_id"] == "until.date" for s in r["senses"]):
            r["senses"].insert(0, UNTIL_DATE)
            changed.append("until: added until.date -> 'cho đến'")
    if r["en"] == "refill":
        if not any(s["sense_id"] == "refill.count" for s in r["senses"]):
            r["senses"].insert(0, REFILL_COUNT)
            changed.append("refill: added refill.count -> 'lần lấy thuốc'")

P.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(changed)} changes, backup at {P.with_suffix('.jsonl.bak2').name}")
for c in changed:
    print("  " + c)
